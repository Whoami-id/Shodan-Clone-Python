from flask import Flask, request, jsonify, Response, render_template_string
import json
from bson.regex import Regex
import re
from pymongo import MongoClient

app = Flask(__name__)
# MongoDB configuration
mongo_uri = "mongodb://localhost:27017/"
client = MongoClient(mongo_uri)

try:
    db = client["scannerdb"]
    collection = db["sslchecker"]
    print("MongoDB connection successful")
except Exception as e:
    print(f"Error connecting to MongoDB: {str(e)}")


@app.errorhandler(Exception)
def handle_database_error(e):
    return "An error occurred while connecting to the database.", 500


# HTML template for the confirmation page with JavaScript
confirmation_template = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Delete Confirmation</title>
  </head>
  <body>
    <h1>Delete Confirmation</h1>
    <p>Are you sure you want to delete all database contents?</p>
    <button id="confirmDelete">Yes</button>
    
    <script>
      const confirmDeleteButton = document.getElementById("confirmDelete");
      confirmDeleteButton.addEventListener("click", function() {
        const confirmed = confirm("Are you sure you want to delete all database contents?");
        if (confirmed) {
          // If user confirms, send a DELETE request to /perform_delete
          fetch("/perform_delete", { method: "DELETE" })
            .then(response => response.json())
            .then(data => {
              alert(data.message);
            })
            .catch(error => {
              console.error(error);
              alert("An error occurred while deleting the database contents.");
            });
        }
      });
    </script>
  </body>
</html>
"""


@app.route("/<path:any_path>", methods=["GET"])
def respond_to_any_path(any_path):
    # Here, 'any_path' will capture any URL path as a variable
    return jsonify({"message": f"Unknown endpoint: {any_path}"})


@app.route("/insert", methods=["POST"])
def insert():
    try:
        # get json data from the request object
        results_json = request.get_json()
        collection.insert_many(results_json)
        return jsonify({"message": "Inserted"})

    except Exception as e:
        print(f"Error inserting data into the database: {str(e)}")
        return jsonify({"error": str(e)}), 500


# http://localhost:5000/bytitle?title=nginx&from=0&to=10
@app.route("/bytitle", methods=["GET"])
def bytitle():
    try:
        title_param = request.args.get("title")

        if title_param is None:
            return jsonify({"error": "title query parameter is missing"}), 400
            # escape any special characters such as dot if it exists in the title_param
        regex_pattern = rf".*{re.escape(title_param)}.*"
        # match the exact value only if it's included in the title
        regex = Regex(regex_pattern, "i")  # "i" flag makes it case-insensitive
        from_index = int(request.args.get("from", 0))
        to_index = int(request.args.get("to", float("inf")))

        # Query MongoDB to find documents with the specified "title" in any key
        query = {
            "$or": [
                {"http_responseForIP.title": regex},
                {"https_responseForIP.title": regex},
                {"http_responseForDomainName.title": regex},
                {"https_responseForDomainName.title": regex},
            ]
        }
        # collection.find returns documents
        matching_entries = list(collection.find(query, {"_id": 0}))
        total_entries = len(matching_entries)
        # Adjust the indices if they are out of bounds
        from_index = max(0, min(from_index, total_entries))
        to_index = min(total_entries, max(to_index, 0))

        # get the entries from:to ,from the entered values in query parameters and remove _id field before returning the response
        paginated_entries = []
        for entry in matching_entries[from_index:to_index]:
            entry.pop("_id", None)
            paginated_entries.append(entry)

        response = {"total_entries": total_entries, "entries": paginated_entries}
        json_response = json.dumps(response, indent=4)

        # Create a Response object with the JSON content type
        return Response(json_response, content_type="application/json")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# http://localhost:5000/bydomain?domain=something.com
@app.route("/bydomain", methods=["GET"])
def bydomain():
    try:
        domain_param = request.args.get("domain")

        if domain_param is None:
            return jsonify({"error": "domain query parameter is missing"}), 400

        regex_pattern = rf".*{re.escape(domain_param)}.*"
        regex = Regex(regex_pattern, "i")

        query = {
            "$or": [
                {"http_responseForIP.domain": regex},
                {"https_responseForIP.domain": regex},
                {"http_responseForDomainName.domain": regex},
                {"https_responseForDomainName.domain": regex},
            ]
        }

        json_data = list(collection.find(query, {"_id": 0}))

        return jsonify(json_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# http://localhost:5000/byip?ip=192.168.0.1
@app.route("/byip", methods=["GET"])
def byip():
    try:
        ip_param = request.args.get("ip")

        if ip_param is None:
            return jsonify({"error": "ip query parameter is missing"}), 400

        regex_pattern = rf".*{re.escape(ip_param)}.*"
        regex = Regex(regex_pattern, "i")

        query = {
            "$or": [
                {"http_responseForIP.ip": regex},
                {"https_responseForIP.ip": regex},
                {"http_responseForDomainName.ip": regex},
                {"https_responseForDomainName.ip": regex},
            ]
        }

        json_data = list(collection.find(query, {"_id": 0}))

        return jsonify(json_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# http://localhost:5000/byport?port=8000&from=0&to=10
@app.route("/byport", methods=["GET"])
def byport():
    try:
        port_param = request.args.get("port")

        if port_param is None:
            return jsonify({"error": "port query parameter is missing"}), 400

        regex_pattern = rf".*{re.escape(port_param)}.*"
        regex = Regex(regex_pattern, "i")
        from_index = int(request.args.get("from", 0))
        to_index = int(request.args.get("to", float("inf")))

        query = {
            "$or": [
                {"http_responseForIP.port": regex},
                {"https_responseForIP.port": regex},
                {"http_responseForDomainName.port": regex},
                {"https_responseForDomainName.port": regex},
            ]
        }

        matching_entries = list(collection.find(query, {"_id": 0}))
        total_entries = len(matching_entries)
        # Adjust the indices if they are out of bounds
        from_index = max(0, min(from_index, total_entries))
        to_index = min(total_entries, max(to_index, 0))

        # get the entries from:to ,from the entered values in query parameters and remove _id field before returning the response
        paginated_entries = []
        for entry in matching_entries[from_index:to_index]:
            entry.pop("_id", None)
            paginated_entries.append(entry)

        response = {"total_entries": total_entries, "entries": paginated_entries}
        json_response = json.dumps(response, indent=4)

        # Create a Response object with the JSON content type
        return Response(json_response, content_type="application/json")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# http://localhost:5000/byhtml?html=welcome to nginx&from=0&to=10
@app.route("/byhtml", methods=["GET"])
def byhtml():
    try:
        html_param = request.args.get("html")

        if html_param is None:
            return jsonify({"error": "html query parameter is missing"}), 400

        regex_pattern = rf".*{re.escape(html_param)}.*"
        regex = Regex(regex_pattern, "i")
        from_index = int(request.args.get("from", 0))
        to_index = int(request.args.get("to", float("inf")))

        query = {
            "$or": [
                {"http_responseForIP.response_text": regex},
                {"https_responseForIP.response_text": regex},
                {"http_responseForDomainName.response_text": regex},
                {"https_responseForDomainName.response_text": regex},
            ]
        }

        matching_entries = list(collection.find(query, {"_id": 0}))
        total_entries = len(matching_entries)
        # Adjust the indices if they are out of bounds
        from_index = max(0, min(from_index, total_entries))
        to_index = min(total_entries, max(to_index, 0))

        # get the entries from:to ,from the entered values in query parameters and remove _id field before returning the response
        paginated_entries = []
        for entry in matching_entries[from_index:to_index]:
            entry.pop("_id", None)
            paginated_entries.append(entry)

        response = {"total_entries": total_entries, "entries": paginated_entries}
        json_response = json.dumps(response, indent=4)

        # Create a Response object with the JSON content type
        return Response(json_response, content_type="application/json")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# gets all the response headers related to the given value in the hresponse query parameter
# Pagination, just apply the size to see the number of results returned
# http://localhost:5000/byhresponse?hresponse=er&from=0&to=10
@app.route("/byhresponse", methods=["GET"])
def byhresponse():
    try:
        hresponse_param = request.args.get("hresponse")

        if hresponse_param is None:
            return jsonify({"error": "hresponse query parameter is missing"}), 400

        from_index = int(request.args.get("from", 0))
        to_index = int(request.args.get("to", float("inf")))
        # get all the documents from DB and convert the result into list
        all_documents = list(collection.find({}))
        matching_entries = []

        # Iterate through each document with a specific key,It first loops http_responseForDomainName, then https_responseForDomainName , then https_responseForIP
        for document in all_documents:
            for keyName in [
                "http_responseForDomainName",
                "https_responseForDomainName",
                "https_responseForIP",
            ]:
                # document.get will return the dictionary associated with the key,eg http_responseForDomainName,in each document we have a field such as http_responseForDomainName so just get that field which is a dictionary
                field = document.get(keyName)
                if field:
                    # loop the keys of each field,since field is a dictionary,we can get the key like this:
                    for key in field:
                        if "response_headers" in key:
                            response_headers = field["response_headers"]
                            for resp_header_value in response_headers.values():
                                if hresponse_param.lower() in resp_header_value.lower():
                                    document["_id"] = str(document["_id"])
                                    matching_entries.append(document)

        # http_responseForIP is an array of objects so I will iterate it
        for document in all_documents:
            # this time document.get will return an array/list of dictionaries
            array_of_dictionaries = document.get("http_responseForIP")
            if array_of_dictionaries:
                for dictionary_item in array_of_dictionaries:
                    for key in dictionary_item:
                        if "response_headers" in key:
                            response_headers = dictionary_item["response_headers"]
                            for header_value in response_headers.values():
                                if hresponse_param.lower() in header_value.lower():
                                    document["_id"] = str(document["_id"])
                                    matching_entries.append(document)

        total_entries = len(matching_entries)

        # Adjust the indices if they are out of bounds
        from_index = max(0, min(from_index, total_entries))
        to_index = min(total_entries, max(to_index, 0))

        # get the entries from:to ,from the entered values in query parameters and remove _id field before returning the response
        paginated_entries = []
        for entry in matching_entries[from_index:to_index]:
            entry.pop("_id", None)
            paginated_entries.append(entry)

        response = {"total_entries": total_entries, "entries": paginated_entries}
        # Manually serialize to JSON and guarantee the order of the returned key/value pairs
        json_response = json.dumps(response, indent=4)

        # Create a Response object with the JSON content type
        return Response(json_response, content_type="application/json")

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Search by keys in the response header
# http://localhost:5000/byhkeyresponse?hkeyresponse=Content-Security-Policy&from=0&to=10
@app.route("/byhkeyresponse", methods=["GET"])
def byhkeyresponse():
    try:
        hkeyresponse_param = request.args.get("hkeyresponse")

        if hkeyresponse_param is None:
            return jsonify({"error": "hresponse query parameter is missing"}), 400

        from_index = int(request.args.get("from", 0))
        to_index = int(request.args.get("to", float("inf")))
        # get all the documents from DB and convert the result into list
        all_documents = list(collection.find({}))
        matching_entries = []

        for document in all_documents:
            for keyName in [
                "http_responseForDomainName",
                "https_responseForDomainName",
                "https_responseForIP",
            ]:
                # document.get will return the dictionary associated with the key,eg http_responseForDomainName,in each document we have a field such as http_responseForDomainName so just get that field which is a dictionary
                field = document.get(keyName)
                if field:
                    # loop the keys of each field,since field is a dictionary,we can get the key like this:
                    for key in field:
                        if "response_headers" in key:
                            response_headers = field["response_headers"]
                            for resp_key_value in response_headers.keys():
                                if hkeyresponse_param.lower() in resp_key_value.lower():
                                    document["_id"] = str(document["_id"])
                                    matching_entries.append(document)

        for document in all_documents:
            array_of_dictionaries = document.get("http_responseForIP")
            if array_of_dictionaries:
                for dictionary_item in array_of_dictionaries:
                    for key in dictionary_item:
                        if "response_headers" in key:
                            response_headers = dictionary_item["response_headers"]
                            for header_key in response_headers.keys():
                                if hkeyresponse_param.lower() in header_key.lower():
                                    document["_id"] = str(document["_id"])
                                    matching_entries.append(document)

        total_entries = len(matching_entries)

        # Adjust the indices if they are out of bounds
        from_index = max(0, min(from_index, total_entries))
        to_index = min(total_entries, max(to_index, 0))

        # get the entries from:to ,from the entered values in query parameters and remove _id field before returning the response
        paginated_entries = []
        for entry in matching_entries[from_index:to_index]:
            entry.pop("_id", None)
            paginated_entries.append(entry)

        response = {"total_entries": total_entries, "entries": paginated_entries}
        # Manually serialize to JSON and guarantee the order of the returned key/value pairs
        json_response = json.dumps(response, indent=4)

        # Create a Response object with the JSON content type
        return Response(json_response, content_type="application/json")

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# route to delete the entire MongoDB collection, you can use this before making a new search of subnets to clear the DB
@app.route("/delete", methods=["GET"])
def delete():
    return render_template_string(confirmation_template)


# JavaScript code in the template will call this function
@app.route("/perform_delete", methods=["DELETE"])
def perform_delete():
    try:
        # Delete all documents in the collection
        result = collection.delete_many({})

        return jsonify({"message": f"Deleted {result.deleted_count} documents"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # In production set debug=False
    app.run(host="0.0.0.0", port=5000, debug=True)
