Create a Python-Flask backend that borrows the shape of our PolicyMe restapi template without copying it wholesale.

The goal of this project is to demonstrate an example of contract first development. We want to use an OpenAPI spec file to automatically generate types on both the frontend and the backend. We then want to use those types to properly type the network communication between the different systems in a completely type-safe way.

Backend should be a Python-Flask REST API with an OpenAPI spec file. 

These endpoints should be defined on the OpenAPI spec file and their types should be used to generate pydantic types in the codebase to be used to add type safety to the blueprints. The goal is to have the types that are enforced on the implementation to be directly derived from the contract.
