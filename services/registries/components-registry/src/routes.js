const express = require('express')
const controller = require('./controls')

const componentsRouter = express.Router()

const exec_request = async (req, resp, class_, func) => {
    const payload = req.body
    if (!payload) {
        return resp.status(500).json({
            error : true,
            message : "Invalid body"
        })
    } else {
        const classInstance = new class_()
        const result = await classInstance[func](payload)
        if (result.error) {
            return resp.status(500).json({
                error : true,
                message : result.m
            })
        }

        return resp.status(200).json({
            error : false,
            payload : result.m
        })
    }
}

//define REST Endpoints:
componentsRouter.post('/registerComponent', async (req, resp) => {
    return await exec_request(req, resp, controller.ComponentsController, "createComponent")
})

componentsRouter.post('/unregisterComponent', async (req, resp) => {
    return await exec_request(req, resp, controller.ComponentsController, "removeComponent")
})

componentsRouter.post("/updateComponent", async (req, resp) => {
    return await exec_request(req, resp, controller.ComponentsController, "updateComponent")
})

componentsRouter.post("/addMetadata", async (req, resp) => {
    return await exec_request(req, resp, controller.ComponentsController, "addMetadata")
})

componentsRouter.post("/updateMetadata", async (req, resp) => {
    return await exec_request(req, resp, controller.ComponentsController, "updateMetadata")
})

componentsRouter.post("/getByType", async (req, resp) => {
    return await exec_request(req, resp, controller.ComponentsController, "findComponentsByType")
})

componentsRouter.post("/getByURI", async (req, resp) => {
    return await exec_request(req, resp, controller.ComponentsController, "findComponentsByURI")
})

componentsRouter.post("/query", async (req, resp) => {
    return await exec_request(req, resp, controller.ComponentsController, "query")
})

componentsRouter.post("/validate", async (req, resp) => {
    return await exec_request(req, resp, controller.ComponentsController, "validateSettingsAndParameters")
})

module.exports.componentRouter = componentsRouter
