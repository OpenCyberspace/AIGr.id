from subprocess import call
import shlex


REDIS_HELM = "redis/"

class HelmSubprocessApi :

    @staticmethod
    def DeployFramedbWithHelm(releaseName, valuesPath, namespace = "framedb", create_new_namespace = True) :

        args = "helm install {} {}".format(releaseName, REDIS_HELM)
        if create_new_namespace :
            args += " --create-namespace=true "

        args += "--insecure-skip-tls-verify "
        args += "--namespace={} ".format(namespace)
        args += "--values={} ".format(valuesPath)
        args += "--version=11.2.1"

        args_shx = shlex.split(args)
        
        #execute helm executor
        call(args_shx)
    
    @staticmethod
    def RemoveDeployment(releaseName, namespace) :

        args = "helm uninstall {} --namespace={}".format(
            releaseName, namespace
        ) 

        args_shx = shlex.split(args)

        call(args_shx)
        





