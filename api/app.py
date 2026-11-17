import hashlib
import json
import os
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ.get("TABLE_NAME", "VolunteerManagement"))

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
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


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    path = event.get("rawPath", "")
    query_params = event.get("queryStringParameters") or {}

    if method == "OPTIONS":
        return response(200, {"message": "OK"})

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"error": "Invalid JSON payload"})

    # 1. LOGIN ROUTE (Fixed order so legacy accounts get auto-assigned password123)
    if method == "POST" and (path.endswith("/login") or path == "/login"):
        staff_id = str(body.get("staff_id", "")).strip().upper()
        password = str(body.get("password", ""))

        if not staff_id or not password:
            return response(400, {"error": "Staff ID and password are required."})

        pk = f"VOL#{staff_id}"
        staff = table.get_item(Key={"PK": pk, "SK": "PROFILE"}).get("Item")

        if not staff:
            return response(401, {"error": "Invalid Staff ID or Password."})

        # Check if the account is deactivated first
        if staff.get("IsActive") is False:
            return response(403, {"error": "Your account has been deactivated. Contact your administrator."})

        stored_password = staff.get("Password")
        
        # LEGACY SUPPORT: If profile was created before passwords existed
        if not stored_password:
            default_hash = hash_password("password123")
            table.update_item(
                Key={"PK": pk, "SK": "PROFILE"},
                UpdateExpression="SET Password = :p, IsActive = :act",
                ExpressionAttributeValues={":p": default_hash, ":act": True}
            )
            stored_password = default_hash

        if stored_password != hash_password(password):
            return response(401, {"error": "Invalid Staff ID or Password."})

        return response(200, {
            "message": "Login successful",
            "staff_id": staff.get("StaffId"),
            "full_name": staff.get("FullName"),
            "role": staff.get("Role", "STAFF")
        })

    # 2. STAFF REGISTRATION ROUTE
    if method == "POST" and path.endswith("/volunteers"):
        staff_id = str(body.get("staff_id") or body.get("id") or "").strip().upper()
        full_name = str(body.get("full_name") or body.get("name") or "").strip()
        role = str(body.get("role") or body.get("skills") or "STAFF").strip().upper()
        password = str(body.get("password", "password123")).strip()
        skills = body.get("skills", [])

        if not staff_id or not full_name:
            return response(400, {"error": "staff_id and full_name are required."})

        pk = f"VOL#{staff_id}"

        try:
            table.put_item(
                Item={
                    "PK": pk,
                    "SK": "PROFILE",
                    "StaffId": staff_id,
                    "FullName": full_name,
                    "Role": role,
                    "Password": hash_password(password),
                    "Skills": skills,
                    "IsActive": True,
                },
                ConditionExpression="attribute_not_exists(PK)",
            )
            return response(201, {"message": f"Staff {staff_id} ({full_name}) registered as {role}."})
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return response(409, {"error": f"Staff ID '{staff_id}' is already taken."})
            raise

    # 3. TOGGLE STAFF STATUS ROUTE (Admin active/deactivate)
    if method == "POST" and path.endswith("/volunteers/status"):
        target_staff_id = str(body.get("staff_id", "")).strip().upper()
        is_active = body.get("is_active")

        if not target_staff_id or is_active is None:
            return response(400, {"error": "staff_id and is_active status are required."})

        pk = f"VOL#{target_staff_id}"
        
        try:
            table.update_item(
                Key={"PK": pk, "SK": "PROFILE"},
                UpdateExpression="SET IsActive = :val",
                ExpressionAttributeValues={":val": bool(is_active)},
                ConditionExpression="attribute_exists(PK)"
            )
            status_word = "activated" if is_active else "deactivated"
            return response(200, {"message": f"Staff {target_staff_id} has been {status_word} successfully."})
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return response(404, {"error": f"Staff ID '{target_staff_id}' not found."})
            raise

    # 4. ADMIN RESET PASSWORD ROUTE
    if method == "POST" and path.endswith("/volunteers/password"):
        target_staff_id = str(body.get("staff_id", "")).strip().upper()
        new_password = str(body.get("password", "")).strip()

        if not target_staff_id or not new_password:
            return response(400, {"error": "staff_id and new_password are required."})

        pk = f"VOL#{target_staff_id}"
        try:
            table.update_item(
                Key={"PK": pk, "SK": "PROFILE"},
                UpdateExpression="SET Password = :p",
                ExpressionAttributeValues={":p": hash_password(new_password)},
                ConditionExpression="attribute_exists(PK)"
            )
            return response(200, {"message": f"Password reset successfully for staff {target_staff_id}."})
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return response(404, {"error": f"Staff ID '{target_staff_id}' not found."})
            raise

    # 5. LOG SHIFT ROUTE
    if method == "POST" and (path.endswith("/shifts") or path.endswith("/shifts/log")):
        staff_id = str(body.get("staff_id") or body.get("vol_id") or "").strip().upper()
        date = str(body.get("date", "")).strip()
        shift_type = str(body.get("shift_type") or body.get("shift_id") or "").strip().upper()
        hours = body.get("hours")
        status = str(body.get("status", "SCHEDULED")).strip().upper()

        if not staff_id or not date or not shift_type or hours is None:
            return response(400, {"error": "staff_id, date, shift_type, and hours are required."})

        pk = f"VOL#{staff_id}"
        existing_staff = table.get_item(Key={"PK": pk, "SK": "PROFILE"}).get("Item")
        if not existing_staff:
            return response(404, {"error": f"Staff ID '{staff_id}' does not exist."})

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

    # 6. GET VOLUNTEERS (Fixed to include is_active property for admin buttons)
    if method == "GET" and path.endswith("/volunteers"):
        result = table.scan(FilterExpression=Attr("SK").eq("PROFILE"))
        staff_list = []
        for item in result.get("Items", []):
            staff_list.append({
                "staff_id": item.get("StaffId") or item["PK"].replace("VOL#", ""),
                "full_name": item.get("FullName") or "N/A",
                "role": item.get("Role", "STAFF"),
                "is_active": item.get("IsActive", True),
            })
        return response(200, {"volunteers": staff_list})

    # 7. GET SHIFTS ROUTE
    if method == "GET" and path.endswith("/shifts"):
        filter_staff_id = query_params.get("staff_id")
        
        if filter_staff_id:
            result = table.query(
                KeyConditionExpression="PK = :pk",
                ExpressionAttributeValues={":pk": f"VOL#{filter_staff_id.upper()}"}
            )
            items = result.get("Items", [])
        else:
            items = table.scan().get("Items", [])

        profiles = {item["PK"]: item for item in items if item.get("SK") == "PROFILE"}
        
        shifts_list = []
        for item in items:
            if str(item.get("SK", "")).startswith("SHIFT#"):
                pk = item["PK"]
                profile = profiles.get(pk, {})
                full_name = item.get("FullName") or profile.get("FullName") or "N/A"
                role = item.get("Role") or profile.get("Role") or "STAFF"

                shifts_list.append({
                    "staff_id": item.get("StaffId") or pk.replace("VOL#", ""),
                    "full_name": full_name,
                    "role": role,
                    "date": item.get("Date") or item["SK"].split("#")[1],
                    "shift_type": item.get("ShiftType") or item["SK"].split("#")[2],
                    "hours": item.get("Hours", 0),
                    "status": item.get("Status", "SCHEDULED"),
                })
        return response(200, {"shifts": shifts_list})

    return response(404, {"error": "Route not found"})