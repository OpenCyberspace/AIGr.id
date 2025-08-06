const mongoose = require('mongoose')

// Sub-schema for componentId
const componentIdSchema = new mongoose.Schema({
  name: { type: String, required: true }, // Component name
  version: { type: String, required: true }, // Component version
  releaseTag: { type: String, required: true }  // Component release tag
}, { _id: false })

// Sub-schema for containerRegistryInfo
const containerRegistryInfoSchema = new mongoose.Schema({
  containerImage: { type: String, required: true }, // Image path in registry
  containerRegistryId: { type: String, required: true }, // Registry identifier
  containerImageMetadata: { type: mongoose.SchemaTypes.Mixed, default: {} }, // Arbitrary metadata (description, author, etc.)
  componentMode: { type: String, enum: ['aios', 'third_party'], required: true }, // Component origin

  // init container: specified only if the componentMode = "third_party"
  initContainer: { type: mongoose.SchemaTypes.Mixed, default: {} }

}, { _id: false })

const componentSchema = new mongoose.Schema({
  createdAt: { type: Date, default: Date.now }, // Creation timestamp (sys generated)
  lastModifiedAt: { type: Date, default: Date.now }, // Last modified timestamp (sys generated)

  componentId: { type: componentIdSchema, required: true }, // Structured component identity
  componentType: { type: String, required: true },

  // Unique URI (assigned internally - system generated) - {<componentType>.<componentId.name>:<componentId.version>-<componentId.releaseTag}
  componentURI: { type: String, required: true, index: true }, 

  containerRegistryInfo: { type: containerRegistryInfoSchema, required: false }, // Container registry information

  componentMetadata: { type: mongoose.SchemaTypes.Mixed, default: {} }, // Custom metadata

  componentInitData: { type: mongoose.SchemaTypes.Mixed, default: {} }, // Initial data/config needed to start
  componentInputProtocol: { type: mongoose.SchemaTypes.Mixed, default: {} }, // Input protocol or data schema
  componentOutputProtocol: { type: mongoose.SchemaTypes.Mixed, default: {} }, // Output protocol or data schema
  policies: { type: mongoose.SchemaTypes.Mixed, default: {} }, // Attached policies

  componentManagementCommandsTemplate: { type: mongoose.SchemaTypes.Mixed, default: {} }, // List of management commands supported
  componentInitSettings: { type: mongoose.SchemaTypes.Mixed, default: {} }, // Runtime settings or flags
  componentParameters: { type: mongoose.SchemaTypes.Mixed, default: {} }, // Param list for inference or processing

  componentInitSettingsProtocol: { type: mongoose.SchemaTypes.Mixed, default: {} }, // Protocol/template of init settings
  componentInitParametersProtocol: { type: mongoose.SchemaTypes.Mixed, default: {} }, // Protocol/template of init params

  tags: [{ type: String }] // Free-form list of tags for search/filtering
})

const Component = mongoose.model("Component", componentSchema)

module.exports.Component = Component
