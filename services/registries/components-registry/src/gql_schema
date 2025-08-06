const { Component } = require('./schema');

const ComponentTc = require('./schema').ComponentTC
const ComponentAll = require('./schema').Component

const ComponentQuery = {
    componentById: ComponentTc.mongooseResolvers.findById({
        lean: true
    }),
    componentByIds: ComponentTc.mongooseResolvers.findByIds({
        lean: true
    }),
    componentOne: ComponentTc.mongooseResolvers.findOne({
        lean: true
    }),
    componentMany: ComponentTc.mongooseResolvers.findMany({
        lean: true
    }),
    componentCount: ComponentTc.mongooseResolvers.count({
        lean: true
    }),
    componentConnection: ComponentTc.mongooseResolvers.connection({
        lean: true
    }),
    componentPagination: ComponentTc.mongooseResolvers.pagination({
        lean: true
    }),
};

const ComponentMutations = {
    /*
        Writes are not supported with GraphQL for components registry,
        This is a future work
    */  
}
module.exports.ComponentQuery = ComponentQuery
module.exports.ComponentMutations = ComponentMutations
