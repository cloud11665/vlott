import json
from fastapi import Response

def json_obj_response(data):
	return Response(content = json.dumps(data, ensure_ascii = False, default=str),
		media_type = "application/json"
	)

