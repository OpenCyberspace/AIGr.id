const Cluster = require('./schema');

// Create a new cluster document
const createCluster = async (data) => {
    try {
        const cluster = new Cluster(data);
        const result = await cluster.save();
        return result;
    } catch (error) {
        throw error;
    }
};

// Read a cluster document by id
const readCluster = async (id) => {
    try {
        const cluster = await Cluster.findOne({ id: id });
        return cluster;
    } catch (error) {
        throw error;
    }
};

// Update a cluster document by id
const updateCluster = async (id, data) => {
    try {
        const result = await Cluster.findOneAndUpdate({ id: id }, data, { new: true });
        return result;
    } catch (error) {
        throw error;
    }
};

// Delete a cluster document by id
const deleteCluster = async (id) => {
    try {
        const result = await Cluster.findOneAndDelete({ id: id });
        return result;
    } catch (error) {
        throw error;
    }
};

// Execute a generic MongoDB query
const executeQuery = async (query) => {
    try {
        const result = await Cluster.find(query);
        return result;
    } catch (error) {
        throw error;
    }
};


module.exports = {
    createCluster,
    readCluster,
    updateCluster,
    deleteCluster,
    executeQuery,
};
