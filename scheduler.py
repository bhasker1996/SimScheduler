import json
import os

import boto3
import urllib3
from aws_lambda_powertools import Logger
from bender.sim import SIM
from requests_aws4auth import AWS4Auth
from os import environ

# from ccs_sim_scheduler.api import get_members



logger = Logger(service="ccs_sim_scheduler")
S3_BUCKET_NAME = os.environ.get("BUCKET_NAME")
s3_client = boto3.client("s3")
OBJECT_KEY = os.environ.get("OBJECT_KEY")
OBJECT_KEY_ref = os.environ.get("OBJECT_KEY_ref")


ALLOWLISTED_ORIGIN = "https://shariasi.people.amazon.dev"



bands = {
    "band1": [
        "88049a58-f4d6-47ea-aed8-317d7f92b9fb",    
        "1df7515c-1271-48c7-9bb3-e2066252fa35",    
        "aa9ada6f-7331-410d-8557-1faafbd5f6f8",    
        "0dc1a566-6c33-4ac1-a156-89df1b5a9392",   
        "d292afcb-2ce4-426f-a73a-fb71cd909e91",   
        "74a8f701-6665-4b5a-9cc4-59968109e62d",   
        "fbcedc45-7949-4870-b331-d4f753b60363",   
        "63b7bf6b-a53b-408d-8d3d-0bfb7568b59d",    
        "c690f3d1-a36c-49bf-8e2e-e8b61cd46654",    
        "fb1a62c8-a5b7-490c-b887-bda9e5b7a1c6",   
        "873ea482-3f9d-42b9-861f-7569bca03c86",    
        "4568d830-f7ca-4ae0-9685-eab7ba8effe7",   
    ],
    "band2": [
        "59ede341-2ad0-4ad6-a03a-525798353cd1",    
        "5e40c7af-c7bb-47d9-9fe3-b429adc7f3d8",    
        "031122f6-2b10-4855-b717-93383386ff40",     
        "a3cce2fb-6876-4ee1-94f1-d4ddb176ca3a",     
        "697dbfbd-8026-4d75-b2cd-c0a3c55d8553",    
        # "7d31e407-adce-4803-8a22-fc0a347610ef",    
        "72e795eb-296f-41ca-996e-4ca8ec2db1e4",
    ],
    "band3": ["8092dc4e-72dd-4209-9694-9748c3ab0598",         
              "51a32aa9-2b5f-4255-8c2e-4b09f8679d02",         
              "3a711958-0acc-47db-b3f7-d764b1219c41",          
              ],                                              
    "norma": ["16b89d07-f5ad-40af-81f5-d4d55855507c","1ac92a32-48a5-4db3-960e-d8c8e97bb3f1", "cf957788-1b72-4c06-ac80-799ae1a3ea5b"],      
    "ams" : "fbb6014c-854a-4715-8ca2-ba459d5bc17e",                                                
    "spc": "b10c2a21-d3b7-4c7b-91fe-c719d8454800",                                                
}


object_keys = {
    "band1": os.environ.get("BAND1"),       # This will give band1.txt from the lambda - env variables
    "band2": os.environ.get("BAND2"),
    "band3": os.environ.get("BAND3"),
    "norma": os.environ.get("NORMA"),
    "spc" : os.environ.get("SPC"),
    "ams" : os.environ.get("AMS")
}


def get_sim_client():
    maxis = "xxxxxxxxx.com"
    session = boto3.Session()
    credentials = session.get_credentials()

    auth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        "us-east-1",
        "sim",
        session_token=credentials.token,
    )

    sim_conn = SIM(auth=auth, api_endpoint=maxis, region="us-east-1")

    return sim_conn




# Finding to which folder the SIM assigned to
def get_assigned_folder(sim_id, sim_client):
    """
    Get the assigned folder for a simulation ID
    
    Args:
        sim_id: Simulation ID
        sim_client: Simulation client object
        
    Returns:
        str: Decoded assigned folder name or None if error occurs
    """
    
    try:
        print(" INSIDE GET ASSIGNED FOLDER ")
        assigned_folder = sim_client.get_issue(issue_id=sim_id).assigned_folder
        print(f"Inside get_assigned_folder, Assigned_folder = {assigned_folder}, assigned_folder_decode = {assigned_folder.decode()}")
        return assigned_folder.decode()

    except Exception as e:
        print(f"Error in get_assigned_folder: {str(e)}")
        return None




def find_band(sim_id, sim_client):
    assigned_folder = get_assigned_folder(sim_id, sim_client)
    try:
        band = [band for band, folders in bands.items() if assigned_folder in folders][0]       # This will give which BAND the sim was assigned to, from the dict written above
        # band_list = []
        # for band, folders in bands.items():
        #     if assigned_folder in folders:
        #         band_list.append(band)
        
        print(f"band = {band}")

        logger.info(f"SIM ID - {sim_id} belongs to {band.split('.')[0]}")
    except IndexError:
        logger.error(f"Not able to determine the band. Folder Id - {assigned_folder}")
        return None

    return band, object_keys.get(band)        # This will give the band1.txt from the lambda func - env variables




def get_cors_headers():
    """
    Service owner is responsible for restricting cors request headers
    """

    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Origin": ALLOWLISTED_ORIGIN,
        "Access-Control-Allow-Methods": "GET",
        "Access-Control-Allow-Headers": "Content-Type",
    }


def internal_error(message: str):
    """Internal Server Failure Response

    Args:
        message (str): info about the error
    """
    return {
        "statusCode": 500,
        "headers": get_cors_headers(),
        "body": json.dumps({"error": message}),
    }



def key_exist(key) -> bool:
    """Check if key exists in s3

    Args:
        key (str): Object key

    Returns:
        bool: True or False
    """
    key_list = s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=key)
    if "Contents" in key_list:
        return True
    else:
        return False




def get_previous_assignee(key) -> str:
    """Gets next assignee from s3 object

    Raises:
        FileNotFoundError: If object was not found

    Returns:
        str: alias of team
    """
    # if key_exist(key):
    #     next_assignee = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=key)["Body"].read()
    # else:
    #     logger.info("Key doesn't exists. Creating key in S3")
    #     raise FileNotFoundError

    # return next_assignee.decode()

    try:
        print(f"printing bucket_name = {S3_BUCKET_NAME}")
        print(f"printing key = {key}")
        if key_exist(key):
            response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=key)
            next_assignee = response["Body"].read()
            return next_assignee.decode()
        else:
            logger.info("Key doesn't exists. Creating key in S3")
            raise FileNotFoundError(f"File {key} not found in bucket {S3_BUCKET_NAME}")
    except Exception as e:
        logger.error(f"Error reading from S3: {str(e)}")
        raise




def upload_file_s3(content: str, key) -> None:
    """Uploads the file to s3

    Args:
        content (str): Next member alias
    """
    with open(f"/tmp/{key}", "w") as f:
        f.write(content)
    s3_client.upload_file(f"/tmp/{key}", S3_BUCKET_NAME, key)





def get_members(key):  #   getting members from the bucket with the prefix
    """
    Returns the members list
    """
    if not key_exist(OBJECT_KEY):
        return internal_error("Object key is not availabe in s3")
    members = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=key)["Body"].read()    

    response_body = json.loads(members.decode())    
    print("headers", get_cors_headers())
    print("body", json.dumps(response_body))
    return {"statusCode": 200, "headers": get_cors_headers(), "body": json.dumps(response_body)}



def get_next_member(key, band):             # Here key represents which band either band1.txt or norma.txt or ams.txt etc.... like that
    """Gets the next member of the team

    Returns:
        str: next team member
    """

    try:
        print(f"Printing the Band itself = {band}")
        print(f"Printing the KEY Itself = {key}")


        # Get previous assignee in that particular band or config
        previous_assignee = get_previous_assignee(key)
        print("=================================================================================================================")
        print("Printing previous assignee == ", previous_assignee)
        print("=================================================================================================================")


        # Get team_members depends on the configuration either SPC, NORM or BANDS etc...
        result = json.loads(get_members(OBJECT_KEY)['body'])
        result_ref = json.loads(get_members(OBJECT_KEY_ref)['body'])
        print("Printing the result after getting the members WITH ONLY BODY",band,  (result))
        print("=================================================================================================================")
        
        if band == "spc":
            print("Sim belongs to SPC Program")
            team_members = result['spc_members']
            team_members_ref = result_ref['spc_members']
            print(f"Printing the SPC members = {team_members}")
        elif band == "ams":
            print("Sim belongs to AMS")
            team_members = result['ams_members']
            team_members_ref = result_ref['ams_members']
            print(f"Printing the AMS members = {team_members}")
        elif band == "norma":
            print("Sim belongs to Normalization Program")
            team_members = result['norm_members']
            team_members_ref = result_ref['norm_members']
            print(f"Printing the Normalization members = {team_members}")
        else:
            print("Sim belongs to CCS")
            team_members = result['ccs_members']
            team_members_ref = result_ref['ccs_members']
            print(f"Printing the CCS members = {team_members}")


        #Need to check whether the person is present on a day and then decide to get the next assignee.
        if previous_assignee in team_members:                                           # This is necessary since at time of leaves we tend to remove names from the s3 bucket so to check if previous assignee was present on the day when the simscheduler is assigning the sim
            print("Previous assignee is present in the team members")
            index = team_members.index(previous_assignee)
            print(f"Printing the index of the previous assignee = {index}")
            if index == len(team_members) - 1:
                print("Previous assignee is the last member of the team")
                next_assignee = team_members[0]
                print(f"Printing the next assignee = {next_assignee}")
            else:
                print("Previous assignee is not the last member of the team")
                next_assignee = team_members[index + 1]
                print(f"Printing the next assignee = {next_assignee}")
        else:
            print("Previous assignee is not present in the team members")
            index = team_members_ref.index(previous_assignee)
            print(f"Printing the index of the previous assignee from ref_members = {index}")
            
            # Start from next person after previous_assignee in team_members_ref
            current_index = (index + 1) % len(team_members_ref)
            
            # Check each person in team_members_ref starting from next position
            for _ in range(len(team_members_ref)):
                candidate = team_members_ref[current_index]
                if candidate in team_members:
                    next_assignee = candidate
                    print(f"Found next assignee from ref who exists in team_members = {next_assignee}")
                    break
                current_index = (current_index + 1) % len(team_members_ref)
            else:
                # If no one from team_members_ref is in team_members, fallback to first member
                next_assignee = team_members[0] if team_members else team_members_ref[0]
                print(f"No ref member found in team_members, using fallback = {next_assignee}")

        upload_file_s3(next_assignee, key)

        return next_assignee
    
    except Exception as e:
        print(f"Error in get_next_member: {str(e)}")
        return None
    
    finally:
        print("execution finished")
        
    


def init_assign(sim_id, sim_client):
    band, key = find_band(sim_id, sim_client)             # This will get the band1.txt from lambda func - env variables. => key is like band1.txt
    print(f" INSIDE init_assign BAND = {band}, KEY = {key}")
    # print(f"Printing type of BAND & KEY, Type of band = {type(band)}, Type of key = {type(key)}" )
    next_member = get_next_member(key,band)
    # assign it to this next_member
    print("printing the next member from INIT ASSIGN = ",next_member)
    #write assign function for this alone!
    assign(sim_id, next_member, sim_client)
    return None


def is_reopened(sim_id, sim_client):
    # Reopening the SIM
    current_assignee = sim_client.get_issue(issue_id=sim_id).assigned_to
    print(f"current assignee = {current_assignee}")

    # if current_assignee is None:
    #     return False

    # assignee_value = getattr(current_assignee, "value", current_assignee)
    # print(f"assignee_value = {assignee_value}")

    # valid_members = FULL_MEMBERS    #set().union(ccs_members, ams_members, spc_members, norm_members)

    # return assignee_value in valid_members, 

    if current_assignee is None:
        return False, current_assignee

    return True, current_assignee



def assign(sim_id, alias, sim_client):
    """Assigns SIM to given alias

    Args:
        sim_id (str): Unique id of the SIM
        alias (str): Id of the team member

    Returns:
        str: Response
    """
    logger.info(f"Assigned {sim_id} to {alias}")
    try:
        payload = [
            {
                "editAction": "PUT",
                "path": "/assigneeIdentity",
                "data": f"kerberos:{alias}@ANT.AMAZON.COM",
            }
        ]
        query = json.dumps({"pathEdits": payload})

        response = sim_client.api_post(f"issues/{sim_id}/edits", query)

        http = urllib3.PoolManager()

        overview = sim_client.get_issue(issue_id=sim_id).description.decode()
        main_id = sim_client.get_issue(issue_id=sim_id).main_id
        title = sim_client.get_issue(issue_id=sim_id).title

        mcm_body = {
            "simId": f"https://issues.amazon.com/{main_id}",
            "overview": f"{overview}",
            "assignee": f"{alias}",
            "title": f"{title}",
        }
        print(f"MCM Body : {mcm_body}")
        print()
        mcm_response = http.request(
            "POST",
            "http://MCMCli-Servi-1t4l7jq85Mar-36f114bf804a7981.elb.us-west-2.amazonaws.com:8080/cpcs/mcm",
            body=json.dumps(mcm_body),
            headers={"Content-Type": "application/json"},
        )

        print(f"MCM Response : {mcm_response.data}")
        print(f"MCM Response Status : {mcm_response.status}")

        if int(mcm_response.status) == 200 or int(mcm_response.status) == 202:
            mcm_id = json.loads(mcm_response)["MCMId"]

            correspondence = f"Please find the MCM raised - https://mcm.amazon.com/cms/{mcm_id}"

            print(f"Adding correspondence - {correspondence} to the SIM - {main_id}")
            sim_client.add_conversation_to_sim(main_id, correspondence)

        return response

    except Exception as e:
        logger.error(e)
        return None



def version6(event, context):
    try:
        print("Event ===>>>>>>>", event)
        sim_client = get_sim_client()
       
        print(f" printing sim_client = {sim_client}")

        for record in event["Records"]:
            msg = json.loads(record["Sns"]["Message"])
            sim_id = msg["documentId"]["id"]
            action = msg["action"]
            updated_fields = record["Sns"]["MessageAttributes"]["updated_fields"]["Value"]
            print(f"Inside Version3,  Printing updated_fields = {updated_fields}")

        print(" INSIDE VERSION3 ")

        assigned, assignee = is_reopened(sim_id, sim_client)

        print(f"Inside version3  ==>>>>  assigned = {assigned},  assignee = {assignee}")

        if assigned:
            return None

        if action == "Create":
            return init_assign(sim_id, sim_client)
        elif action == "Modify" and "/assignedFolder" in updated_fields:
            return init_assign(sim_id, sim_client)
        elif action == "Modify" and "assignee" in updated_fields:
            return init_assign(sim_id, sim_client)

        # init_assign("CCS-20858", sim_client)
        # previous_assignee = get_previous_assignee("band2.txt")
        # print(f"previous assignee = {previous_assignee}")

        return None

    except Exception as e:
        print(f"Error processing SNS event: {str(e)}")
        # You might want to add more context to the error message
        print(f"Failed for simulation ID: {sim_id if 'sim_id' in locals() else 'Unknown'}")
        return None


# if(__name__) == "__main__":
#     version6("ads","sdfa")

```
NOTE : Please note that some of the code was removed intentionally due to complaince issues.
```
