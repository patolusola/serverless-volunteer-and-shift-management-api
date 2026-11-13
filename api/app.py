import json
import os
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ.get("TABLE_NAME", "VolunteerManagement"))

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://d1ue1aryz7nwkm.cloudfront.net",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Content-Type": "application/json",
}


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    path = event.get("rawPath", "")

    if method == "OPTIONS":
        return response(200, {"message": "OK"})

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"error": "Invalid JSON payload"})

    # Add new staff and block duplicate Staff IDs
    if method == "POST" and path.endswith("/volunteers"):
        staff_id = str(body.get("staff_id") or body.get("id") or "").strip().upper()
        full_name = str(body.get("full_name") or body.get("name") or "").strip()
        role = str(body.get("role") or body.get("skills") or "").strip()
        skills = body.get("skills", [])

        if not staff_id or not full_name or not role:
            return response(400, {"error": "staff_id, full_name, and role are required."})

        pk = f"VOL#{staff_id}"

        try:
            table.put_item(
                Item={
                    "PK": pk,
                    "SK": "PROFILE",
                    "StaffId": staff_id,
                    "FullName": full_name,
                    "Role": role,
                    "Skills": skills,
                },
                ConditionExpression="attribute_not_exists(PK)",
            )
            return response(201, {"message": f"Staff {staff_id} ({full_name}) registered successfully."})
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return response(409, {"error": f"Staff ID '{staff_id}' is already taken. Choose another ID."})
            raise

    # Log shifts and reject unregistered Staff IDs
    if method == "POST" and (path.endswith("/shifts") or path.endswith("/shifts/log")):
        staff_id = str(body.get("staff_id") or body.get("vol_id") or "").strip().upper()
        date = str(body.get("date", "")).strip()
        shift_type = str(body.get("shift_type") or body.get("shift_id") or "").strip().upper()
        hours = body.get("hours")
        status = str(body.get("status", "SCHEDULED")).strip().upper()

        if not staff_id or not date or not shift_type or hours is None:
            return response(400, {"error": "staff_id, date, shift_type, and hours are required."})

        pk = f"VOL#{staff_id}"

        # Verify the volunteer profile exists first
        existing_staff = table.get_item(Key={"PK": pk, "SK": "PROFILE"}).get("Item")
        if not existing_staff:
            return response(404, {"error": f"Staff ID '{staff_id}' does not exist. Register the staff member first."})

        table.put_item(
            Item={
                "PK": pk,
                "SK": f"SHIFT#{date}#{shift_type}",
                "StaffId": staff_id,
                "FullName": existing_staff.get("FullName", ""),
                "Role": existing_staff.get("Role", ""),
                "Date": date,
                "ShiftType": shift_type,
                "Hours": Decimal(str(hours)),
                "Status": status,
            }
        )
        return response(201, {"message": f"Shift logged for {existing_staff.get('FullName')} ({staff_id})."})

    # Get all registered staff (Staff ID, Full Name, Role, Skills)
    if method == "GET" and path.endswith("/volunteers"):
        result = table.scan(FilterExpression=Attr("SK").eq("PROFILE"))
        staff_list = [
            {
                "staff_id": item.get("StaffId") or item["PK"].replace("VOL#", ""),
                "full_name": item.get("FullName", "N/A"),
                "role": item.get("Role", "N/A"),
                "skills": item.get("Skills", []),
            }
            for item in result.get("Items", [])
        ]
        return response(200, {"volunteers": staff_list})

    # Get all logged shifts
    if method == "GET" and path.endswith("/shifts"):
        result = table.scan(FilterExpression=Attr("SK").begins_with("SHIFT#"))
        shifts_list = [
            {
                "staff_id": item.get("StaffId") or item["PK"].replace("VOL#", ""),
                "full_name": item.get("FullName", "N/A"),
                "role": item.get("Role", "N/A"),
                "date": item.get("Date") or (item["SK"].split("#")[1] if len(item["SK"].split("#")) > 1 else ""),
                "shift_type": item.get("ShiftType") or (item["SK"].split("#")[2] if len(item["SK"].split("#")) > 2 else ""),
                "hours": item.get("Hours", 0),
                "status": item.get("Status", "N/A"),
            }
            for item in result.get("Items", [])
        ]
        return response(200, {"shifts": shifts_list})

    return response(404, {"error": "Route not found"})