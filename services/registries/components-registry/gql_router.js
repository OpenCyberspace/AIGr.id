/* const buildSchema = require('graphql').buildASTSchema
const gql_express = require('express-graphql')
const express = require('express')
const path = require('path')
const fs = require('fs')
const schemaBuilders = require('./src/gql_builder').builderSchema
const queryResolvers = require('./src/gql_schema').ComponentQuery

const build_schema = () => {
    const schemaPath = path.join(__dirname, "./data/schema.graphql.txt")
    if (!fs.existsSync(schemaPath)) {
        return null
    }

    const schemaString = fs.readFileSync(schemaPath).toString("utf-8")
    console.log(schemaString)
    const schema = buildSchema(schemaString)
    return schema
}

const ql_router = express.Router()
ql_router.use("/", gql_express.graphqlHTTP({
    schema: schemaBuilders,
    graphiql: true,
    rootValue: queryResolvers
}))

module.exports.ql_router = ql_router */