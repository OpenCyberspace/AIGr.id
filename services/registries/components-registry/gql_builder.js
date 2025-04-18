const fs = require('fs')
const path = require('path')
const graphql = require('graphql').graphql

const introspectionQuery = require('graphql/utilities').introspectionFromSchema
const printSchema = require('graphql/utilities').printSchema

const schemaBuilder = require('./src/gql_builder').builderSchema

const buildSchema = async () => {
    fs.writeFileSync(
        path.join(__dirname, './data/schema.graphql.json'),
        JSON.stringify(await graphql(schemaBuilder, introspectionQuery), null, 2)
    );

    fs.writeFileSync(
        path.join(__dirname, './data/schema.graphql.txt'),
        printSchema(schemaBuilder)
    );
}

const run = async () => {
    await buildSchema();
    console.log('Schema build complete!');
}

run().catch(e => {
    console.log(e);
    process.exit(0);
});