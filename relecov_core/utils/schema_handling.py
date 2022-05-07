import json
import re
from django.db import DataError
from relecov_core.models import Schema, SchemaProperties, PropertyOptions
from relecov_core.utils.generic_functions import store_file
from relecov_core.core_config import SCHEMAS_UPLOAD_FOLDER, ERROR_INVALID_JSON, ERROR_INVALID_SCHEMA, ERROR_SCHEMA_ALREADY_LOADED, SCHEMA_SUCCESSFUL_LOAD


def load_schema(json_file):
    """Store json file in the defined folder and store information in database"""
    data = {}
    try:
        data["full_schema"] = json.load(json_file)
    except json.decoder.JSONDecodeError:
        return {"ERROR": ERROR_INVALID_JSON}
    data["file_name"] = store_file(json_file, SCHEMAS_UPLOAD_FOLDER)
    return data


def check_heading_valid_json(schema_data, m_structure):
    """Check if json have at least the main structure"""
    for item in m_structure:
        try:
            schema_data[item]
        except KeyError:
            return False
    return True


def store_schema_properties(schema_obj, s_properties, required):
    """Store the properties defined in the schema"""
    for prop_key in s_properties.keys():

        data = dict(s_properties[prop_key])
        data["schemaID"] = schema_obj
        data["property"] = prop_key
        if prop_key in required:
            data["required"] = True
        if "Enums" in data:
            data["options"] = True
        try:
            new_property = SchemaProperties.objects.create_new_property(data)
        except (KeyError, DataError) as e:
            import pdb; pdb.set_trace()
            schema_obj.delete()
            return {"ERROR": e}
        if "options" in data:
            for item in s_properties[prop_key]["Enums"]:
                enum = re.search(r'(.+) \[(.*)\]', item)
                e_data = {"enums": enum.group(1), "ontology": enum.group(2)}
                e_data["propertyID"] = new_property
                try:
                    PropertyOptions.objects.create_property_options(e_data)
                except (KeyError, DataError) as e:
                    import pdb; pdb.set_trace()
                    schema_obj.delete()
                    return {"ERROR": e}
    return {"SUCCESS" : ""}


def process_schema_file(json_file, version, user, apps_name):
    """ Check json file and store in database"""
    schema_data = load_schema(json_file)
    if "ERROR" in schema_data:
        return schema_data
    # store root data of json schema

    structure = ["schema", "required", "type", "properties"]
    if not check_heading_valid_json(schema_data["full_schema"], structure):
        return {"ERROR": ERROR_INVALID_SCHEMA}

    schema_name = schema_data["full_schema"]["schema"]
    if Schema.objects.filter(schema_name__iexact=schema_name, schema_version__iexact=version, schema_apps_name__exact=apps_name).exists():
        return {"ERROR": ERROR_SCHEMA_ALREADY_LOADED}
    data = {"schema_name": schema_name, "file_name": schema_data["file_name"], "schema_version": version, 'schema_app_name': apps_name, "user_name": user}
    new_schema = Schema.objects.create_new_schema(data)
    result = store_schema_properties(new_schema, schema_data["full_schema"]["properties"], schema_data["full_schema"]["required"])
    if "ERROR" in result:
        return result
    import pdb; pdb.set_trace()
    return {"SUCCESS": SCHEMA_SUCCESSFUL_LOAD}
