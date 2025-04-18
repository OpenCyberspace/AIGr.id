import json
import os
import glob



def load_templates_from_directory(path: str):
    if not os.path.exists(path):
        return False, "Path {} not found".format(path)
    # load all templates from that directory:
    templates = glob.glob("{}/*.json".format(path))
    return True, templates


class Templates:

    def __init__(self, template_path: str, logger):

        self.logger = logger

        ret, templates = load_templates_from_directory(template_path)
        if not ret:
            self.logger.error(action="load_templates",
                              severity=ErrorSeverity.HIGH, message=templates,
                              exception=Exception("Failed to load templates")
                              )

            self.templates = None
        else:
            self.tempaltes = templates
            self.template_path = template_path
        self.templates_map = {}

    def build_templates(self):
        try:

            # load templates for each template
            for template in self.tempaltes:
                template_json = json.load(open(template))
                # parse headers and load the template:
                header = template_json['header']
                # get template id string
                object_id = header['objectId']
                uid = header['uid']

                # prepare template URI
                template_uri = "{}.{}.{}".format(
                    object_id['objectType'],
                    object_id['templateType'],
                    object_id['subType']
                )

                # parse uid
                template_uri = "{}.{}:{}-{}".format(
                    template_uri,
                    uid['id'],
                    uid['version'],
                    uid['releaseTag']
                )

                # read the spec:
                spec = template_json['spec']

                # get top-level object name
                sepc_type = spec['@type']

                # populate the map
                self.templates_map[template_uri] = {
                    "spec": spec,
                    "top_level_type": sepc_type
                }

            self.logger.info(
                action="load_templates",
                message="Finished parsing templates"
            )

            return True, "Templates built"

        except Exception as e:
            self.logger.error(action="load_templates",
                              severity=ErrorSeverity.HIGH, message=str(e),
                              exception=e
                              )
            # raise e
            return False, str(e)


# data-type definitions and validation rules:
class Validators:

    def __init__(self, tmpl_map):
        self.type_map = {
            "number": self.validate_i,
            "boolean": self.validate_boolean,
            "choice": self.validate_choices,
            "reference": self.validate_references,
            "array": self.validate_array,
            "object": self.validate_object,
            "templateReference": self.validate_template,
            "string": self.validate_string,
            "any": self.bypass_any
        }

        self.tmpl_map = tmpl_map

        # stack-trace data:
        self.current_template = None
        self.current_template_name = None
        self.current_field = None
        self.current_data = None
        self.current_key = None
        self.current_dtype = None

    def __call_validator(self, t: str, d, key: str, tmpl: dict) -> (bool, str):

        self.current_template = tmpl
        self.current_field = key
        self.current_data = d
        self.current_dtype = t

        if t not in self.type_map:
            return False, "Invalid type {}".format(t)

        d_dict = {"key": key, "value": d}
        return self.type_map[t](d_dict, tmpl)

    def bypass_any(self, data: dict, templ: dict) -> (bool, str):
        return True, "bypassed"

    def validate_i(self, data: dict, templ: dict) -> (bool, str):
        number = data['value']

        print(number)
        key = data['key']
        if type(number) != int:
            if type(number) != float:
                return False, "{} is not a number for {}".format(
                    number, key
                )

        # check if it is a range value:
        if 'range' in templ:
            rng = templ['range']
            if rng['minimum'] != -1 and number < rng['minimum']:
                return False, "{} is less than minium for {}".format(
                    number, key
                )
            if rng['maximum'] != -1 and number > rng['maximum']:
                return False, "{} is greater than maximum for {}".format(
                    number, key
                )

        if 'choices' in templ:
            choices = templ['choices']
            if number not in choices:
                return False, "{} is not a valid choice for {} in {}".format(
                    number, key, choices
                )

        return True, "Validation pass"

    def validate_boolean(self, data: dict, templ: dict) -> (bool, str):
        flag = data['value']
        if type(flag) != bool:
            return False, "{} is not a boolean for {}".format(
                flag, data['key']
            )
        return True, "Validation pass"

    def validate_object(self, od: dict, templ: dict) -> (bool, str):

        print(od)

        data = od['value']
        key = od['key']

        if type(data) != dict:
            return False, "{} is not an object for {}".format(
                key, data
            )

        # iterate over required keys:
        objectFields = templ['objectFields']
        for field in objectFields:
            # skip metadata, this will be used by mapper to map runtime db
            if field == "@templateMetadata":
                continue

            print('validating ', field)
            sub_template = objectFields[field]
            if 'required' in sub_template and sub_template['required']:
                if field not in data:
                    return False, "Field {} required, but missing".format(
                        field
                    )

            if field not in data:
                continue
            # dispatch based on method, for each key in template:
            data_value = data[field]
            ret, result = self.__call_validator(
                sub_template['@type'], data_value, field,
                sub_template
            )

            if not ret:
                return False, result

        return True, "Validation pass"

    def validate_references(self, data: dict, templ: dict) -> (bool, str):
        reference = data['value']
        key = data['key']

        if type(reference) != str:
            return False, "{} is not a string for {}".format(
                reference, key
            )
        # check substring method:
        matchResult = False
        refPrefixes = templ['referencePrefix']
        for refPrefix in refPrefixes:
            refPrefix = refPrefix.replace("*", "")
            matchResult = matchResult or (refPrefix in reference)

        if not matchResult:
            return False, "Reference {} does not match any {}".format(
                reference, refPrefixes
            )

        return True, "validation pass"

    def validate_template(self, od: dict, templ: dict) -> (bool, str):

        data = od['value']
        key = od['key']

        if type(data) != dict:
            return False, "{} is not template for {}".format(
                data, key
            )

        # check template type:
        specifiedType = data['@templateType']
        possibleTypes = templ['referencePrefix']

        checkResult = False
        for possibleType in possibleTypes:
            possibleType = possibleType.replace("*", "")
            checkResult = checkResult or (possibleType in specifiedType)

        if not checkResult:
            return False, "{} is not allowed, required types {}".format(
                specifiedType, possibleTypes
            )

        # map to template and parse the values:
        if specifiedType not in self.tmpl_map:
            return False, "Template {} is not registered".format(
                specifiedType
            )
        # get the values and verify it's type against object
        template_ref = self.tmpl_map[specifiedType]
        if template_ref['top_level_type'] != 'object':
            return False, "Template spec must be object type"

        spec_values = data['values']

        self.current_template_name = specifiedType

        # pass to object validator:
        ret, result = self.__call_validator(
            "object", spec_values, "spec",
            template_ref['spec']
        )

        if not ret:
            return False, result

        return True, "Validaion pass"

    def validate_string(self, od: dict, templ: dict) -> (bool, str):

        data = od['value']
        key = od['key']

        if type(data) != str:
            return False, "{} is not a string for {}".format(
                data, key
            )

        if 'choices' in templ:
            choices = templ['choices']
            if data not in choices:
                return False, "{} is not a choice for {}, allowed {}".format(
                    data, key, choices
                )

        return True, "Validation passed"

    def validate_choices(self, data: dict, templ: dict) -> (bool, str):
        return True, "validation passed"

    def validate_array(self, data: dict, templ: dict) -> (bool, str):
        array = data['value']
        key = data['key']

        if type(array) != list:
            return False, "{} is not a list for {}".format(
                array, key
            )

        arraydtype = templ['@elementType']
        for element in array:
            objFields = None
            if "objectFields" in templ:
                objFields = templ['objectFields']

            ret, result = self.__call_validator(
                arraydtype, element, key,
                {
                    "@type": arraydtype,
                    "objectFields": objFields
                }
            )

            if not ret:
                return False, result

        return True, "Validation passed"


def parse_vdag_input(input_data: dict) -> (bool, str, dict):
    if 'header' not in input_data:
        return False, "Invalid input, must contain header", None

    if 'spec' not in input_data:
        return False, "Invalid input must contain spec", None

    # return the spec
    if 'uid' not in input_data['header']:
        return False, "No UID in specification", None

    # parse UID to get the stirng repr
    uid = input_data['header']['uid']
    uid = "vdag-{}.{}:{}".format(
        uid['id'], uid['version'], uid['releaseTag']
    )

    return True, uid, input_data['spec']


class V1PolicyRuleParser:
    def __init__(self, templates_dir: str, logger):

        self.templates_dir = templates_dir
        self.logger = logger

        self.TemplateClass = Templates
        self.ValidatorClass = Validators

        self.template_instance = None
        self.validator_instance = None

    def load_templates(self) -> (bool, str):

        self.template_instance = self.TemplateClass(
            self.templates_dir,
            self.logger
        )

        if not self.template_instance.tempaltes:
            return False, "Failed to load templates for V1Parser"

        # call build templates
        ret, res = self.template_instance.build_templates()
        if not ret:
            return False, "Failed to load templates for V1Parser"

        return True, "Loaded templates"

    def create_validator_and_validate(self, spec) -> (bool, str):

        try:
            self.vi = self.ValidatorClass(
                self.template_instance.templates_map
            )

            # get top level template from spec:
            top_template = spec['@templateType']
            if top_template not in self.template_instance.templates_map:
                return False, "Template {} not found for ParserV1".format(
                    top_template
                )

            template_table_ref = self.template_instance.templates_map
            template_spec_ref = template_table_ref[top_template]

            if template_spec_ref['top_level_type'] != 'object':
                return False, "Top level template must be object type"

            template_spec_ref = template_spec_ref['spec']

            # set initial stack trace info:
            self.vi.current_template_name = top_template
            self.vi.current_template = template_spec_ref
            self.vi.current_data = spec['values'],
            self.vi.current_dtype = 'object',
            self.vi.current_key = 'spec'
            self.vi.current_field = 'spec'

            # run validation from template:
            ret, result = self.vi.validate_object(
                {"value": spec['values'], "key": "spec"},
                templ=template_spec_ref
            )

            print(result)

            if not ret:
                # get current stack-trace:
                stack_trace = {
                    "error_in_template": self.vi.current_template_name,
                    "error_subtemplate": self.vi.current_template,
                    "error_in_field": self.vi.current_field,
                    "error_in_data": self.vi.current_data,
                    "main_key": self.vi.current_key,
                    "required_dtype": self.vi.current_dtype
                }

                return False, {"trace": stack_trace, "message": result}
            return True, result
        except Exception as e:
            self.logger.error(
                action="validation", severity=ErrorSeverity.HIGH,
                message=str(e),
                exception={"parser_version": "Parser/v1"}
            )

            return True, str(e)

    def validate_and_return_templates(self, spec) -> (bool, dict):

        ret, result = self.create_validator_and_validate(spec)
        return ret, result, self.template_instance.templates_map

