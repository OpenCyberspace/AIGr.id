const mongoose = require('mongoose');
const { Schema } = mongoose;

// Define the cluster schema
const clusterSchema = new Schema({
    id: { type: String, required: true, unique: true },
    regionId: { type: String, required: true },
    nodes: {
        count: { type: Number, required: true },
        nodeData: [{ type: Schema.Types.Mixed, required: false }]
    },
    gpus: {
        count: { type: Number, required: true },
        memory: { type: Number, required: true }
    },
    vcpus: {
        count: { type: Number, required: true }
    },
    memory: { type: Number, required: true },
    swap: { type: Number, required: true },
    storage: {
        disks: { type: Number, required: true },
        size: { type: Number, required: true }
    },
    network: {
        interfaces: { type: Number, required: true },
        txBandwidth: { type: Number, required: true },
        rxBandwidth: { type: Number, required: true }
    },
    config: { type: Schema.Types.Mixed, required: false },
    tags: { type: [String], required: true },
    clusterMetadata: { type: Schema.Types.Mixed, required: true },
    reputation: { type: Number, required: true },
});

const Cluster = mongoose.model('Cluster', clusterSchema);

module.exports = Cluster;
