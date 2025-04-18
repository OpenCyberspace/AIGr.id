const schemas = require('./schema')


const valueValidator = (key, validationRule, provided) => {
    const suppliedValue = provided
    // 2.1 handle string types:
    if (validationRule['type'] === 'string') {
        if (typeof suppliedValue !== 'string') {
            return { error: true, m: `Key ${key} is expected to be a string, but got ${typeof suppliedValue}` }
        } else {
            // the string is present, check if the validation rule contains 'options'
            if (validationRule.options) {
                const options = validationRule.options
                if (!options.includes(suppliedValue)) {
                    return { error: true, m: `Key ${key} is expected to contain ${options}, but got ${suppliedValue}` }
                }
            }

            return { error: false, m: suppliedValue }
        }
    }

    if (validationRule['type'] === 'int' || validationRule['type'] === 'float') {
        if (typeof suppliedValue !== 'number') {
            return { error: true, m: `Key ${key} is expected to be an int or float, but got ${typeof suppliedValue}` }
        } else {
            // check if there are min and max values
            if (validationRule.min && suppliedValue < validationRule.min) {
                return { error: true, m: `Key ${key} is expected to be gte ${validationRule.min}, but got ${suppliedValue}` }
            }

            if (validationRule.max && suppliedValue > validationRule.max) {
                return { error: true, m: `Key ${key} is expected to be lte ${validationRule.max} but got ${suppliedValue}` }
            }

            return { error: false, m: suppliedValue }
        }
    }

    if (validationRule['type'] == 'bool') {
        if (typeof suppliedValue !== 'boolean') {
            return { error: true, m: `Key ${key} is expected to be a boolean, but got ${typeof suppliedValue}` }
        }

        return {error: false, m: suppliedValue}
    }

    if (validationRule['type'] == 'any') {
        return { error: false, m: suppliedValue }
    }

    if (validationRule['type'] == 'array') {
        if (!Array.isArray(suppliedValue)) {
            return { error: true, m: `Key ${key} is expected to be an array, but got ${typeof suppliedValue}` }
        }

        if (validationRule.size && suppliedValue.length !== validationRule.size) {
            return { error: true, m: `Key ${key} is expected to be an array of size ${validationRule.size} but got ${suppliedValue.length}` }
        }

        // validate each element
        if (!validationRule.subtype) {
            return {error: false, m: suppliedValue}
        }

        const newValidatedArray = []
        for (var x = 0; x < suppliedValue.length; x++) {
            const result = valueValidator(key, validationRule.subtype, suppliedValue[x])
            if (result.error) {
                return result
            }

            newValidatedArray.push(result.m)
        }

        return {error: false, m: newValidatedArray}
    }

    if (validationRule['type'] == 'object') {
        if (typeof suppliedValue !== 'object') {
            return { error: true, m: `Key ${key} is expected to be an object, but got ${typeof suppliedValue}` }
        }

        // validate this object
        if (!validationRule.subtype) {
            return {error: false, m: suppliedValue}
        }

        const rules = validationRule.subtype
        const result = valuesValidator(rules, suppliedValue)
        if (result.error) {
            return result
        }

        return {error: false, m: result.m}
    }

    return {error: false, m: suppliedValue}
}


const valuesValidator = (originalRules, supplied) => {
    // iterate over the original object

    const newSupplied = supplied

    for (var idx = 0; idx < originalRules.length; idx++) {
        const validationRule = originalRules[idx]
        const key = validationRule.name

        console.log(`validating ${key}, ${validationRule}, ${supplied}`)

        // Case-1: key is not there in supplied parameters
        if (!supplied[key]) {
            if (validationRule.required) {
                if (!validationRule.default) {
                    return { error: true, m: `Key ${key} is required, it is not provided and no default value is specified.` }
                } else {
                    newSupplied[key] = validationRule.default
                }
            } else if (validationRule.default) {
                newSupplied[key] = validationRule.default
            }
        } else {
            // Case-2: The key if found, check it's rule:
            const result = valueValidator(key, validationRule, supplied[key])
            if (result.error) {
                return result
            }

            newSupplied[key] = result.m
        }
    }

    return {error: false, m: newSupplied}
}

class ComponentsController {

    createURI(componentId, componentType) {
        const suffix = `${componentId.name}:${componentId.version}-${componentId.release}`
        return `${componentType}.${suffix}`
    }

    async checkIfComponentExist(componentId, componentType) {
        const uri = this.createURI(componentId, componentType)
        try {
            const result = await schemas.Component.findOne({ componentURI: uri })
            if (!result) {
                throw "Not exist"
            }
            return { error: false, m: result }
        } catch (err) {
            return { error: true, m: err }
        }
    }

    async createComponent(payload) {
        try {

            const componentURI = this.createURI(
                payload.componentId, payload.componentType
            )

            payload.componentURI = componentURI

            const component = new schemas.Component(payload)
            await component.validate()

            // check if uri already exist:
            const checkExistResult = await this.checkIfComponentExist(
                component.componentId,
                component.componentType
            )

            if (!checkExistResult.error) {
                throw `Component with URI ${checkExistResult.m.componentURI} already exists.`
            }

            // save to DB
            const result = await component.save()
            return { error: false, m: result }

        } catch (err) {
            return { error: true, m: err }
        }
    }

    async updateComponent(updatePayload) {
        try {

            const componentURI = updatePayload.uri
            const updateData = updatePayload.data

            if (!componentURI || !updateData) {
                throw "Invalid payload received, it should contain uri and data"
            }

            const updateResult = schemas.Component.updateOne(
                { componentURI: componentURI },
                updateData
            )

            if (updateData) {
                return { error: false, m: updateResult }
            }

            throw "Failed to update document"

        } catch (err) {
            return { error: true, m: err }
        }
    }

    async removeComponent(payload) {
        try {

            const componentURI = payload.uri
            if (!componentURI) {
                throw "Invalid payload, it should contain uri and data"
            }

            const deleteResult = await schemas.Component.deleteOne({
                "componentURI": componentURI
            })

            if (!deleteResult) {
                throw "Failed to delete componen"
            }

            return { error: false, m: deleteResult }

        } catch (err) {
            return { error: true, m: err }
        }
    }

    async updateMetadata(updatePayload) {
        try {

            const componentURI = updatePayload.uri
            const metadata = updatePayload.data

            if (!componentURI || !metadata) {
                throw "Invalid payload received, it should contain uri and data"
            }

            const updateResult = schemas.Component.updateOne(
                { componentURI: componentURI },
                { metadata: metadata }
            )

            if (updateResult) {
                return { error: false, m: updateResult }
            }

            throw "Failed to update metadata"

        } catch (err) {
            return { error: true, m: err }
        }
    }

    async addMetadata(updatePayload) {

        try {

            const componentURI = updatePayload.uri
            const metadata = updatePayload.data

            if (!componentURI || !metadata) {
                throw "Invalid payload received, it should contain uri and data"
            }

            //validate against metadata
            const metadataObj = new schemas.Metadata(metadata)
            await metadataObj.validate()

            const updateResult = schemas.Component.updateOne(
                { componentURI: componentURI },
                { metadata: metadata }
            )

            if (updateResult) {
                return { error: false, m: updateResult }
            }

            throw "Failed to update metadata"

        } catch (err) {
            return { error: true, m: err }
        }
    }

    async findComponentsByType(payload) {
        try {

            const componentType = payload.typeString
            if (!componentType) {
                throw "Invalid payload received, it should contain typeString"
            }

            const queryResult = await schemas.Component.find({
                "componentType": { "$regex": componentType }
            })

            return { error: false, m: queryResult }

        } catch (err) {
            return { error: true, m: err }
        }
    }

    async findComponentsByURI(payload) {
        try {

            const componentURI = payload.uriString
            if (!componentURI) {
                throw "Invalid payload received, it should contain uriString"
            }

            const queryResult = await schemas.Component.find({
                "componentURI": { "$regex": componentURI }
            })

            return { error: false, m: queryResult }

        } catch (err) {
            return { error: true, m: err }
        }
    }

    async query(payload) {
        try {

            const queryPayload = payload.query
            if (!queryPayload) {
                throw "Invalid payload received, it should contain query"
            }

            console.log(queryPayload)

            const queryResult = await schemas.Component.find(queryPayload)

            return { error: false, m: queryResult }

        } catch (err) {
            return { error: true, m: err }
        }
    }

    async validateSettingsAndParameters(payload) {
        try {

            // get the component:
            const componentUri = payload.componentUri
            const givenSettings = payload.settings
            const givenParameters = payload.parameters

            let finalSettings = {}
            let finalParameters = {}

            const queryResult = await schemas.Component.findOne({ "componentURI": componentUri })
            if (!queryResult) {
                throw `${componentUri} does not exist`
            }

            console.log(queryResult)

            // validate the component:
            const componentConfig = queryResult.componentConfig

            // are there any settings?
            if (!componentConfig.settings || componentConfig.settings.length == 0) {
                finalSettings = givenSettings
            } else {
                const result = valuesValidator(componentConfig.settings, givenSettings)
                if (result.error) {
                    return result
                }

                finalSettings = result.m
            }

            if (!componentConfig.parameters || componentConfig.parameters.length == 0) {
                finalParameters = givenParameters
            } else {

                const result = valuesValidator(componentConfig.parameters, givenParameters)
                if (result.error) {
                    return result
                }

                finalParameters = result.m
            }

            return {error: false, m: {
                settings: finalSettings,
                parameters: finalParameters
            }}

        } catch (err) {
            console.log(err)
            return { error: true, m: err }
        }
    }
}



module.exports.ComponentsController = ComponentsController