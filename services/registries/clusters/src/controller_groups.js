const mongoose = require('mongoose');
const Group = require('./models/group'); // Import the Group model

// Helper function to merge objects
function mergePolicies(policiesArray) {
    return policiesArray.reduce((mergedPolicies, currentPolicy) => {
        return { ...mergedPolicies, ...currentPolicy };
    }, {});
}

// Function to create a group and update parent groups' child arrays and group policies
async function createGroup(data) {
    const { group_id, group_uri, group_search_tags, group_metadata, group_description, group_policies, group_parent_ids } = data;

    try {
        // Step 1: Retrieve all parent groups
        let mergedParentPolicies = {};
        if (group_parent_ids && group_parent_ids.length > 0) {
            const parentGroups = await Group.find({ _id: { $in: group_parent_ids } });

            // Step 2: Extract group_policies from all parent groups and merge them
            const parentPoliciesArray = parentGroups.map(group => group.group_policies);
            mergedParentPolicies = mergePolicies(parentPoliciesArray);
        }

        // Step 3: Merge current object's group_policies with the merged parent policies
        const finalGroupPolicies = mergePolicies([mergedParentPolicies, group_policies]);

        // Step 4: Create the new group with the merged policies
        const newGroup = new Group({
            group_id,
            group_uri,
            group_search_tags,
            group_metadata,
            group_description,
            group_policies: finalGroupPolicies, // Set the final merged policies
            group_parent_ids
        });

        const savedGroup = await newGroup.save();

        // Step 5: Update the parents' group_children_ids
        if (group_parent_ids && group_parent_ids.length > 0) {
            await Group.updateMany(
                { _id: { $in: group_parent_ids } },
                { $addToSet: { group_children_ids: savedGroup._id } }
            );
        }

        return { success: true, group: savedGroup };
    } catch (error) {
        console.error('Error creating group:', error);
        throw new Error('Failed to create group');
    }
}

// Function to remove a group (soft delete by removing its reference from parents)
async function removeGroup(groupId) {
    try {
        // Find the group by its group_id
        const group = await Group.findOne({ group_id: groupId });

        if (!group) {
            throw new Error('Group not found');
        }

        // Step 1: Remove the group's reference from its parents
        if (group.group_parent_ids && group.group_parent_ids.length > 0) {
            await Group.updateMany(
                { _id: { $in: group.group_parent_ids } },
                { $pull: { group_children_ids: group._id } }
            );
        }

        return { success: true, message: 'Group removed from parent references successfully' };
    } catch (error) {
        console.error('Error removing group:', error);
        throw new Error('Failed to remove group');
    }
}

// Function to fully delete a group
async function deleteGroup(groupId) {
    try {
        // Find and delete the group by its group_id
        const deletedGroup = await Group.findOneAndDelete({ group_id: groupId });

        if (!deletedGroup) {
            throw new Error('Group not found');
        }

        // Step 1: Remove the group's reference from its parents
        if (deletedGroup.group_parent_ids && deletedGroup.group_parent_ids.length > 0) {
            await Group.updateMany(
                { _id: { $in: deletedGroup.group_parent_ids } },
                { $pull: { group_children_ids: deletedGroup._id } }
            );
        }

        return { success: true, message: 'Group deleted successfully' };
    } catch (error) {
        console.error('Error deleting group:', error);
        throw new Error('Failed to delete group');
    }
}

// 1. Generic query function
async function queryGroups(query = {}) {
    try {
        const groups = await Group.find(query);
        return { success: true, groups };
    } catch (error) {
        console.error('Error querying groups:', error);
        throw new Error('Failed to query groups');
    }
}

// 2. Get the graph of all child groups given a parent group ID
async function getChildrenGraph(groupId) {
    try {
        // Recursive function to get children of a group
        async function getChildren(group) {
            const children = await Group.find({ _id: { $in: group.group_children_ids } });
            const childrenWithDescendants = await Promise.all(
                children.map(async (child) => ({
                    ...child.toObject(),
                    children: await getChildren(child)
                }))
            );
            return childrenWithDescendants;
        }

        // Find the parent group by ID
        const parentGroup = await Group.findOne({ _id: groupId });
        if (!parentGroup) {
            throw new Error('Parent group not found');
        }

        // Get the full hierarchy (children tree)
        const groupHierarchy = {
            ...parentGroup.toObject(),
            children: await getChildren(parentGroup)
        };

        return { success: true, hierarchy: groupHierarchy };
    } catch (error) {
        console.error('Error fetching children graph:', error);
        throw new Error('Failed to fetch children graph');
    }
}

// 3. Get the graph of all groups given the group ID using the parent link till the root
async function getParentGraph(groupId) {
    try {
        // Recursive function to get parents of a group
        async function getParents(group) {
            const parents = await Group.find({ _id: { $in: group.group_parent_ids } });
            if (parents.length === 0) return []; // No more parents, we've reached the root

            const parentsWithAncestors = await Promise.all(
                parents.map(async (parent) => ({
                    ...parent.toObject(),
                    parents: await getParents(parent)
                }))
            );
            return parentsWithAncestors;
        }

        // Find the current group by ID
        const currentGroup = await Group.findOne({ _id: groupId });
        if (!currentGroup) {
            throw new Error('Group not found');
        }

        // Get the full hierarchy (parent tree)
        const groupAncestry = {
            ...currentGroup.toObject(),
            parents: await getParents(currentGroup)
        };

        return { success: true, ancestry: groupAncestry };
    } catch (error) {
        console.error('Error fetching parent graph:', error);
        throw new Error('Failed to fetch parent graph');
    }
}

module.exports = {
    createGroup,
    removeGroup,
    deleteGroup,
    queryGroups,       
    getChildrenGraph,  
    getParentGraph    
};
