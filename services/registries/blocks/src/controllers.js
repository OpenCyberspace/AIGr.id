const Block = require('./schema');

// Create a new block
exports.createBlock = async (req, res) => {
    try {
        const block = new Block(req.body);
        await block.save();
        res.status(201).json(block);
    } catch (error) {
        res.status(400).json({ message: error.message });
    }
};

// Get all blocks
exports.getAllBlocks = async (req, res) => {
    try {
        const blocks = await Block.find();
        res.status(200).json(blocks);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
};

// Get a block by ID
exports.getBlockById = async (req, res) => {
    try {
        const block = await Block.findOne({id: req.params.id});
        if (!block) {
            return res.status(404).json({ message: 'Block not found' });
        }
        res.status(200).json(block);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
};

// Update a block by ID
exports.updateBlockById = async (req, res) => {
    try {
        const block = await Block.findOneAndUpdate({ id: req.params.id }, req.body, { new: true, runValidators: true });
        if (!block) {
            return res.status(404).json({ message: 'Block not found' });
        }
        res.status(200).json(block);
    } catch (error) {
        res.status(400).json({ message: error.message });
    }
};

// Delete a block by ID
exports.deleteBlockById = async (req, res) => {
    try {
        const block = await Block.findOneAndDelete({id: req.params.id});
        if (!block) {
            return res.status(404).json({ message: 'Block not found' });
        }
        res.status(200).json({ message: 'Block deleted successfully' });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
};

exports.queryBlocks = async (req, res) => {
    try {
        const query = req.body.query || {};
        const options = req.body.options || {};
        const blocks = await Block.find(query, null, options);
        res.status(200).json(blocks);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
};