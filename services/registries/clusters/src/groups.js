const mongoose = require('mongoose');
const Schema = mongoose.Schema;

const GroupSchema = new Schema({
    group_id: {
        type: String,
        required: true,
        unique: true,
        index: true
    },
    group_uri: {
        type: String,
        required: true
    },
    group_search_tags: {
        type: [String],
        required: true
    },
    group_metadata: {
        type: Schema.Types.Mixed, // Allows storing any kind of data
        required: false
    },
    group_description: {
        type: String,
        required: false
    },
    group_policies: {
        type: Schema.Types.Mixed, // Allows storing any kind of data
        required: false
    },
    group_parent_ids: [{
        type: Schema.Types.ObjectId,
        ref: 'Group', // Reference the same Group collection
        required: false
    }],
    group_children_ids: [{
        type: Schema.Types.ObjectId,
        ref: 'Group', // Reference the same Group collection
        required: false
    }]
}, {
    timestamps: true // Automatically adds createdAt and updatedAt fields
});

module.exports = mongoose.model('Group', GroupSchema);