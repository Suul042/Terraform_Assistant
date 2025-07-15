# CI/CD

This project uses GitHub Actions for Continuous Integration and Continuous Deployment (CI/CD).

## Workflow

The CI/CD workflow is defined in the `.github/workflows/ci-cd.yml` file. The workflow is triggered on every push to the `main` branch and on every pull request targeting the `main` branch.

## Stages

The workflow consists of the following stages:

1.  **Lint**: Lints the Python and TypeScript code.
2.  **Test**: Runs the backend and frontend tests.
3.  **Build**: Builds the Docker image for the application.
4.  **Deploy**: Deploys the application to the staging environment.

*TODO: Add more details about the deployment process.*
