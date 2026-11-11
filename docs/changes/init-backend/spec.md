It should expose a couple of endpoints:
- /file-upload
  - takes a single PDF per request
  - uploads it to S3
  - returns an `upload_id` for the uploaded file
- /create-extraction 
  - creates an extraction by submitting the upload_id to our document data extraction system
  - it returns an `extraction_id` which should be saved on the client and should be saved to the database eventually.

We want to create these endpoints and use a relatively simple architecture that should at least mimic the basics of how we do this in product. 

> Remember, this is a only a demonstration repository, we don't actually care about the implementations. Hard-coded responses are completely appropriate given they're behind the right abstractions.

Never write unit tests for anything. Writing tests must be explicitly spelled out by the user.

There are two tutorials relevant to this 
- `docs/research/OpenAPI to Pydantic Types Tutorial.md` which we will refer to as "Type Generation"
- `docs/research/REST API POC Setup Tutorial.md` which we will refer to as "API Setup"

You should follow and apply the steps from API Setup first. Then, overlay any of the changes from Type Generation on top of it.

Type Generation contains examples that use internal `pm_*` libraries (`pm_utils`, `pm_auth`, `pm_lifeconsts`). This POC does not use them. Replace them with plain Flask and Pydantic.

Endpoints return the generated response model directly as JSON, with no `{"status", "data"}` envelope and no `make_success` / `make_error` helpers.

See `plan.md` for the full decision log.
