import copy
import json
from datetime import date, datetime
from json import JSONDecodeError
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint


app = Flask(__name__)
CORS(app)

SWAGGER_URL = "/api/docs"
API_URL = "/static/masterblog.json"
swagger_ui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={"app_name": "Masterblog API"},
)
app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)

POSTS_FILE = Path(__file__).with_name("posts.json")
DEFAULT_POSTS = [
    {
        "id": 1,
        "title": "First post",
        "content": "This is the first post.",
        "author": "Alice",
        "date": "2023-06-07",
    },
    {
        "id": 2,
        "title": "Second post",
        "content": "This is the second post.",
        "author": "Bob",
        "date": "2023-07-15",
    },
]


class StorageError(Exception):
    """Raised when the JSON storage cannot be read or written safely."""


def save_posts(posts):
    """Atomically persist posts as formatted UTF-8 JSON."""
    temporary_file = POSTS_FILE.with_suffix(".tmp")
    try:
        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(posts, file, ensure_ascii=False, indent=2)
            file.write("\n")
        temporary_file.replace(POSTS_FILE)
    except OSError as error:
        raise StorageError("Unable to write the posts file.") from error


def load_posts():
    """Load posts, creating the storage file when it does not yet exist."""
    try:
        with POSTS_FILE.open(encoding="utf-8") as file:
            posts = json.load(file)
    except FileNotFoundError:
        posts = copy.deepcopy(DEFAULT_POSTS)
        save_posts(posts)
        return posts
    except (OSError, JSONDecodeError) as error:
        raise StorageError("Unable to read a valid posts file.") from error

    if not isinstance(posts, list) or not all(isinstance(post, dict) for post in posts):
        raise StorageError("The posts file must contain a JSON list of objects.")

    required_fields = {"id", "title", "content", "author", "date"}
    seen_ids = set()
    for post in posts:
        if not required_fields.issubset(post):
            raise StorageError("Every stored post must contain id, title, content, author and date.")
        if not isinstance(post["id"], int) or post["id"] in seen_ids:
            raise StorageError("Every stored post must have a unique integer id.")
        if not all(isinstance(post[field], str) and post[field].strip() for field in ("title", "content", "author")):
            raise StorageError("Stored title, content and author values must be non-empty strings.")
        if not is_valid_date(post["date"]):
            raise StorageError("Stored dates must use YYYY-MM-DD format.")
        seen_ids.add(post["id"])
    return posts


def next_post_id(posts):
    """Return an integer ID that is unique in the given post list."""
    return max((post["id"] for post in posts), default=0) + 1


def find_post(posts, post_id):
    """Find a post by integer ID or return None."""
    return next((post for post in posts if post.get("id") == post_id), None)


def is_valid_date(value):
    """Return whether value uses the required YYYY-MM-DD format."""
    if not isinstance(value, str):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


@app.errorhandler(StorageError)
def handle_storage_error(error):
    app.logger.error("Storage error: %s", error)
    return jsonify({"error": str(error)}), 500


@app.route("/api/posts", methods=["GET"])
def get_posts():
    posts = load_posts()
    search_query = request.args.get("search", "").strip().lower()
    if search_query:
        posts = [
            post
            for post in posts
            if any(search_query in post[field].lower() for field in ("title", "content", "author", "date"))
        ]

    sort_field = request.args.get("sort")
    direction = request.args.get("direction", "asc")

    if sort_field is None and "direction" not in request.args:
        return jsonify(posts)
    if sort_field not in {"title", "content", "author", "date"}:
        return jsonify({"error": "Invalid sort field. Use title, content, author or date."}), 400
    if direction not in {"asc", "desc"}:
        return jsonify({"error": "Invalid direction. Use asc or desc."}), 400

    def sort_key(post):
        if sort_field == "date":
            return datetime.strptime(post["date"], "%Y-%m-%d")
        return post[sort_field].lower()

    sorted_posts = sorted(posts, key=sort_key, reverse=direction == "desc")
    return jsonify(sorted_posts)


@app.route("/api/posts", methods=["POST"])
def add_post():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    missing_fields = [
        field
        for field in ("title", "content")
        if not isinstance(data.get(field), str) or not data[field].strip()
    ]
    if missing_fields:
        return jsonify({"error": f"Missing required field(s): {', '.join(missing_fields)}"}), 400

    author = data.get("author") or "Anonymous"
    if not isinstance(author, str):
        return jsonify({"error": "author must be a string."}), 400
    author = author.strip() or "Anonymous"
    post_date = data.get("date") or date.today().isoformat()
    if not is_valid_date(post_date):
        return jsonify({"error": "date must use YYYY-MM-DD format."}), 400

    posts = load_posts()
    new_post = {
        "id": next_post_id(posts),
        "title": data["title"].strip(),
        "content": data["content"].strip(),
        "author": author,
        "date": post_date,
    }
    posts.append(new_post)
    save_posts(posts)
    return jsonify(new_post), 201


@app.route("/api/posts/search", methods=["GET"])
def search_posts():
    posts = load_posts()
    title_query = request.args.get("title", "").strip().lower()
    content_query = request.args.get("content", "").strip().lower()
    search_query = request.args.get("search", "").strip().lower()

    matches = [
        post
        for post in posts
        if (title_query and title_query in post["title"].lower())
        or (content_query and content_query in post["content"].lower())
        or (
            search_query
            and any(search_query in str(post[field]).lower() for field in ("title", "content", "author", "date"))
        )
    ]
    return jsonify(matches)


@app.route("/api/posts/<int:post_id>", methods=["GET"])
def get_post(post_id):
    post = find_post(load_posts(), post_id)
    if post is None:
        return jsonify({"error": f"Post with id {post_id} was not found."}), 404
    return jsonify(post)


@app.route("/api/posts/<int:post_id>", methods=["PUT"])
def update_post(post_id):
    posts = load_posts()
    post = find_post(posts, post_id)
    if post is None:
        return jsonify({"error": f"Post with id {post_id} was not found."}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400
    for field in ("title", "content", "author"):
        if field in data and (not isinstance(data[field], str) or not data[field].strip()):
            return jsonify({"error": f"{field} must be a non-empty string."}), 400
    if "date" in data and not is_valid_date(data["date"]):
        return jsonify({"error": "date must use YYYY-MM-DD format."}), 400

    for field in ("title", "content", "author"):
        if field in data:
            post[field] = data[field].strip()
    if "date" in data:
        post["date"] = data["date"]
    save_posts(posts)
    return jsonify(post), 200


@app.route("/api/posts/<int:post_id>", methods=["DELETE"])
def delete_post(post_id):
    posts = load_posts()
    post = find_post(posts, post_id)
    if post is None:
        return jsonify({"error": f"Post with id {post_id} was not found."}), 404

    posts.remove(post)
    save_posts(posts)
    return jsonify({"message": f"Post with id {post_id} has been deleted successfully."}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
