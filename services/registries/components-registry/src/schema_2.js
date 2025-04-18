const mongoose = require('mongoose');

const ComponentMetadataAuthorLinkSchema = new mongoose.Schema({
    linkName: String,
    url: String
}, { _id: false });

const ComponentMetadataAuthorSchema = new mongoose.Schema({
    authorName: String,
    authorEmail: String,
    authorLinks: ComponentMetadataAuthorLinkSchema
}, { _id: false });

const ComponentMetadataSchema = new mongoose.Schema({
    description: String,
    tags: [String],
    license: String,
    author: ComponentMetadataAuthorSchema
}, { _id: false });

const ContainerRegistryInfoSchema = new mongoose.Schema({
    containerImage: String,
    containerRegistryURI: String,
    containerRegistryCredentialsSecretName: String,
    containerRegistryLoginType: String
}, { _id: false });

const GeneralPropertiesSchema = new mongoose.Schema({
    requireFrames: Boolean,
    properties: {
        maxBatchSize: Number,
        maxInputSizeWidth: Number,
        maxInputSizeHeight: Number
    }
}, { _id: false });

const SettingsSchema = new mongoose.Schema({
    enableFP16: {
        type: Boolean,
        default: false
    },
    cudnnBenchmarkMode: {
        type: Boolean,
        default: false
    },
    batchSize: {
        type: Number,
        default: 16
    }
}, { _id: false });

const ParametersSchema = new mongoose.Schema({ type: mongoose.SchemaTypes.Mixed, default: {}, required: false }, { _id: false });

const ConditionSchema = new mongoose.Schema({
    variable: String,
    operator: String,
    value: mongoose.Schema.Types.Mixed
}, { _id: false });

const ResourceConditionsSchema = new mongoose.Schema({
    logicalOperator: String,
    conditions: [ConditionSchema]
}, { _id: false });

const DefaultAllocationsSchema = new mongoose.Schema({
    resource: {
        cluster: ResourceConditionsSchema,
        node: ResourceConditionsSchema
    }
}, { _id: false });

const AssetStorageURIInfoSchema = new mongoose.Schema({
    objectId: String,
    isEncrypted: Boolean,
    encryptionInfo: mongoose.Schema.Types.Mixed,
    accessCredentialsInfo: mongoose.Schema.Types.Mixed
}, { _id: false });

const AssetSchema = new mongoose.Schema({
    assetId: String,
    assetDescription: String,
    assetStorageMode: String,
    assetStorageURIInfo: AssetStorageURIInfoSchema
}, { _id: false });

const AllowedPolicySchema = new mongoose.Schema({
    name: String,
    allowed: [String]
}, { _id: false });

const SupportedCustomMetricsSchema = new mongoose.Schema({
    name: String,
    type: String,
    metricsType: String
}, { _id: false });

const ComponentConfigSchema = new mongoose.Schema({
    general: GeneralPropertiesSchema,
    settings: SettingsSchema,
    parameters: ParametersSchema,
    defaultAllocations: DefaultAllocationsSchema,
    assets: [AssetSchema],
    allowedPolicies: [AllowedPolicySchema],
    supportedCustomMetrics: [SupportedCustomMetricsSchema]
}, { _id: false });

const initContainerSchema = new mongoose.Schema({
    containerImageData: ContainerRegistryInfoSchema,
    containerSettings: mongoose.Schema.Types.Mixed,
    containerParameters: mongoose.Schema.Types.Mixed,
    containerInitData: mongoose.Schema.Types.Mixed
})

const executorContainerSchema = new mongoose.Schema({
    containerImageData: ContainerRegistryInfoSchema,
    containerSettings: mongoose.Schema.Types.Mixed,
    containerParameters: mongoose.Schema.Types.Mixed,
    containerInitData: mongoose.Schema.Types.Mixed
})

const singleInstanceConfig = new mongoose.Schema({
    urlMap: mongoose.Schema.Types.Mixed,
    settings: mongoose.Schema.Types.Mixed,
    parameters: mongoose.Schema.Types.Mixed
})

const singleInstanceBlock = new mongoose.Schema({
    initContainerData: initContainerSchema,
    executorContainerData: executorContainerSchema,
    config: singleInstanceConfig
})

const ComponentSchema = new mongoose.Schema({
    componentId: {
        name: String,
        version: String,
        release: String
    },
    componentType: String,
    componentMode: String,
    componentMetadata: ComponentMetadataSchema,
    componentGeneralSearchTags: [String],
    containerRegistryInfo: ContainerRegistryInfoSchema,
    componentConfig: ComponentConfigSchema,
    singleInstanceComponent: singleInstanceBlock
});

const Component = mongoose.model('Component', ComponentSchema);
const Metadata = mongoose.model("Metadata", ComponentMetadataSchema)

module.exports.Component = Component
module.exports.Metadata = Metadata
module.exports.ComponentTC = gqlComposer.composeMongoose(Component)