const express = require('express');
const router = express.Router();
const blockController = require('./controllers'); 

// Route for creating a new block
router.post('/blocks', blockController.createBlock);

// Route for getting all blocks
router.get('/blocks', blockController.getAllBlocks);

// Route for getting a block by ID
router.get('/blocks/:id', blockController.getBlockById);

// Route for updating a block by ID
router.put('/blocks/:id', blockController.updateBlockById);

// Route for deleting a block by ID
router.delete('/blocks/:id', blockController.deleteBlockById);

// Route for querying blocks
router.post('/blocks/query', blockController.queryBlocks);

module.exports = router;