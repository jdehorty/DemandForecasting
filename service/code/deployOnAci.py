with open("./configuration/config.json") as f:
    config = json.load(f)

workspace_name = config["workspace_name"]
resource_group = config["resource_group"]
subscription_id = config["subscription_id"]
location = config["location"]

cli_auth = AzureCliAuthentication()


# Get workspace
#ws = Workspace.from_config(auth=cli_auth)
ws = Workspace.get(
        name=workspace_name,
        subscription_id=subscription_id,
        resource_group=resource_group,
        auth=cli_auth
    )

env = Environment.get(workspace=ws, name="AzureML-Minimal")
#print(env)

Environment(name="arimaenv")

# From a Conda specification file
arimaenv = Environment.from_conda_specification(name = "arimaenv", file_path = "./scripts/scoring/conda_dependencies.yml")
print(arimaenv)

arimaenv.register(workspace=ws)

# Creates the environment inside a Docker container.
arimaenv.docker.enabled = True

try:
    with open("./configuration/model.json") as f:
        config = json.load(f)
except:
    print("No new model to register thus no need to create new scoring image")
    # raise Exception('No new model to register as production model perform better')
    sys.exit(0)

model_name = config["model_name"]
model_version = config["model_version"]

model_list = Model.list(workspace=ws)
model, = (m for m in model_list if m.version == model_version and m.name == model_name)
print(
    "Model picked: {} \nModel Description: {} \nModel Version: {}".format(
        model.name, model.description, model.version
    )
)

# Combine scoring script & environment in Inference configuration
inference_config = InferenceConfig(entry_script="./scripts/scoring/score.py", environment=arimaenv)

deployment_config = AciWebservice.deploy_configuration(
    cpu_cores=1,
    memory_gb=1,
    tags={"area": "timeseries", "type": "forecasting"},
    description="forecasting using ARIMA",
)

aci_service_name = "arimaaciws" + datetime.datetime.now().strftime("%m%d%H%M")

service = Model.deploy(
    workspace = ws,
    name = aci_service_name,
    models = [model],
    inference_config = inference_config,
    deployment_config = deployment_config)

try:
    service.wait_for_deployment(show_output = True)
except:
    print("**************LOGS************")
    print(service.state)
    print(service.get_logs())


print(
    "Deployed ACI Webservice: {} \nWebservice Uri: {}".format(
        service.name, service.scoring_uri
    )
)




# Writing the ACI details to /aml_config/aci_webservice.json
aci_webservice = {}
aci_webservice["aci_name"] = service.name
aci_webservice["aci_url"] = service.scoring_uri
with open("./configuration/aci_webservice.json", "w") as outfile:
    json.dump(aci_webservice, outfile)
