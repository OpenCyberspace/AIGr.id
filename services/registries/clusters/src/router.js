const express = require('express');
const { createCluster, readCluster, updateCluster, deleteCluster, executeQuery } = require('./controller');

const router = express.Router();

// Create a new cluster
router.post('/clusters', async (req, res) => {
    try {
        const result = await createCluster(req.body);
        res.status(200).json(result);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Read a cluster by id
router.get('/clusters/:id', async (req, res) => {
    try {
        const result = await readCluster(req.params.id);
        if (result) {
            res.status(200).json(result);
        } else {
            res.status(404).json({ error: 'Cluster not found' });
        }
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Update a cluster by id
router.put('/clusters/:id', async (req, res) => {
    try {
        const result = await updateCluster(req.params.id, req.body);
        if (result) {
            res.status(200).json(result);
        } else {
            res.status(404).json({ error: 'Cluster not found' });
        }
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Delete a cluster by id
router.delete('/clusters/:id', async (req, res) => {
    try {
        const result = await deleteCluster(req.params.id);
        if (result) {
            res.status(200).json({ message: 'Cluster deleted' });
        } else {
            res.status(404).json({ error: 'Cluster not found' });
        }
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Execute a generic query
router.post('/clusters/query', async (req, res) => {
    try {
        const result = await executeQuery(req.body.query);
        res.status(200).json(result);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// 1. Route to create a new group
router.post('/groups', async (req, res) => {
    try {
        const groupData = req.body; 
        const result = await groupService.createGroup(groupData);
        res.status(201).json(result);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// 2. Route to remove (soft delete) a group
router.post('/groups/:group_id/remove', async (req, res) => {
    try {
        const groupId = req.params.group_id;
        const result = await groupService.removeGroup(groupId);
        res.status(200).json(result);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// 3. Route to delete (hard delete) a group
router.delete('/groups/:group_id', async (req, res) => {
    try {
        const groupId = req.params.group_id;
        const result = await groupService.deleteGroup(groupId);
        res.status(200).json(result);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// 4. Route for generic query on groups
router.post('/groups/query', async (req, res) => {
    try {
        const query = req.body.query; 
        const result = await groupService.queryGroups(query);
        res.status(200).json(result);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// 5. Route to get the hierarchy of all child groups for a given parent group ID
router.get('/groups/:group_id/children', async (req, res) => {
    try {
        const groupId = req.params.group_id;
        const result = await groupService.getChildrenGraph(groupId);
        res.status(200).json(result);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// 6. Route to get the hierarchy of all parent groups for a given group ID
router.get('/groups/:group_id/parents', async (req, res) => {
    try {
        const groupId = req.params.group_id;
        const result = await groupService.getParentGraph(groupId);
        res.status(200).json(result);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

module.exports = router;
