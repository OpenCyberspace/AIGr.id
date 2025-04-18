const SchemaComposer = require('graphql-compose').SchemaComposer
const ComponentQuery = require('./gql_schema').ComponentQuery
const ComponentMutations = require('./gql_schema').ComponentMutations

const schemaComposer = new SchemaComposer()

schemaComposer.Query.addFields(ComponentQuery)
schemaComposer.Mutation.addFields(ComponentMutations)

module.exports.builderSchema = schemaComposer.buildSchema()

