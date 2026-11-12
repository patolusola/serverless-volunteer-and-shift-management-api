import json
import boto3
import os

# connect to the dynamodb - filing cabinet
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def lambda_handler(event, context):
    route_key = event.get('routeKey', '')
    
    try:
        # Route 1: register a new volunteer
        if route_key == 'POST /volunteers':
            body = json.loads(event['body'])
            table.put_item(
                Item={
                    'PK': f"VOL#{body['id']}",
                    'SK': 'PROFILE',
                    'Name': body['name'],
                    'Skills': body['skills']
                }
            )
            return {'statusCode': 201, 'body': json.dumps({'message': 'Volunteer registered!'})}
            
        # route 2: Log a completed shift
        elif route_key == 'POST /shifts/log':
            body = json.loads(event['body'])
            table.put_item(
                Item={
                    'PK': f"VOL#{body['vol_id']}",
                    'SK': f"SHIFT#{body['date']}#{body['shift_id']}",
                    'Hours': body['hours'],
                    'Status': 'COMPLETED'
                }
            )
            return {'statusCode': 200, 'body': json.dumps({'message': 'Shift logged!'})}
            
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

    return {'statusCode': 404, 'body': json.dumps({'error': 'Route not found'})}