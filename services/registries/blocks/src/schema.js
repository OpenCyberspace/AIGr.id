const mongoose = require('mongoose');


const BlockSchema = new mongoose.Schema({
    id: { type: String, required: true, unique: true },
    componentUri: { type: String },
    component: { type: mongoose.Schema.Types.Mixed },
    blockUri: { type: String },
    blockMetadata: { type: mongoose.Schema.Types.Mixed },
    policies: { type: mongoose.Schema.Types.Mixed },
    cluster: { type: mongoose.Schema.Types.Mixed },
    blockInitData: { type: mongoose.Schema.Types.Mixed },
    initSettings: { type: mongoose.Schema.Types.Mixed },
    parameters: { type: mongoose.Schema.Types.Mixed },
    minInstances: { type: mongoose.Schema.Types.Mixed },
    maxInstances: { type: mongoose.Schema.Types.Mixed },
    inputProtocol: { type: mongoose.Schema.Types.Mixed  },
    outputProtocol: { type: mongoose.Schema.Types.Mixed  },
    tags: { type: mongoose.Schema.Types.Mixed }
});

const Block = mongoose.model('Block', BlockSchema);

module.exports = Block;