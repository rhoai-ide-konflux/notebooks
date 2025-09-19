#!/usr/bin/env python3

import re
import yaml

import gen_gha_matrix_jobs

import gha_pr_changed_files

# poetry run ci/cached-builds/generate_component_defs.py > konflux_components.yaml
# oc apply -f konflux_components.yaml
# open https://console.redhat.com/application-pipeline/access/workspaces/rhoai-ide-konflux

workspace_name = "rhoai-ide-konflux-tenant"
application_name = "rhoai-ide-konflux-notebooks"
git_revision = "main"
git_url = "https://github.com/rhoai-ide-konflux/notebooks"


def konflux_component(component_name, dockerfile_path) -> dict:
    return {
        "apiVersion": "appstudio.redhat.com/v1alpha1",
        "kind": "Component",
        "metadata": {
            "annotations": {
                # create imagerepository,
                # https://redhat-internal.slack.com/archives/C07S8637ELR/p1736436093726049?thread_ts=1736420157.217379&cid=C07S8637ELR
                "image.redhat.com/generate": '{"visibility": "public"}',
                "build.appstudio.openshift.io/pipeline": '{"name":"docker-build-oci-ta","bundle":"latest"}',
                "build.appstudio.openshift.io/status": '{"pac":{"state":"enabled","message":"done"}',
                # "build.appstudio.openshift.io/status": '{"pac":{"state":"enabled","merge-url":"https://github.com/rhoai-ide-konflux/notebooks/pull/13","configuration-time":"Fri, 17 Jan 2025 12:11:55 UTC"},"message":"done"}',
                "git-provider": "github",
                "git-provider-url": "https://github.com",
            },
            "name": component_name,
            "namespace": workspace_name,
            "ownerReferences": [
                {
                    "apiVersion": "appstudio.redhat.com/v1alpha1",
                    "kind": "Application",
                    "name": application_name,
                    "uid": "0dc3161b-b5ee-43e0-bef9-1f50a46f7f9d",
                }
            ],
            "finalizers": [
                "test.appstudio.openshift.io/component",
                "pac.component.appstudio.openshift.io/finalizer",
            ],
        },
        "spec": {
            "application": application_name,
            "componentName": component_name,
            "containerImage": "quay.io/redhat-user-workloads/"
            + workspace_name
            + "/"
            + component_name,
            "resources": {},
            "source": {
                "git": {
                    "dockerfileUrl": dockerfile_path,
                    "revision": git_revision,
                    "url": git_url,
                }
            },
        },
    }


def component_image_repository(component_name: str) -> dict:
    return {
        "apiVersion": "appstudio.redhat.com/v1alpha1",
        "kind": "ImageRepository",
        "metadata": {
            "name": "imagerepository-for-" + application_name + "-" + component_name,
            "namespace": workspace_name,
            # "ownerReferences": [
            #     {
            #         "apiVersion": "appstudio.redhat.com/v1alpha1",
            #         "kind": "Component",
            #         "name": component_name,
            #         # "uid": "ef714826-ee14-40ac-b662-114ae497c5a2",
            #     }
            # ],
            "finalizers": ["appstudio.openshift.io/image-repository"],
            "labels": {
                "appstudio.redhat.com/application": application_name,
                "appstudio.redhat.com/component": component_name,
            },
        },
        "spec": {
            "image": {
                "name": workspace_name + "/" + component_name,
                "visibility": "public",
            },
            "notifications": [
                {
                    "config": {
                        "url": "https://bombino.api.redhat.com/v1/sbom/quay/push"
                    },
                    "event": "repo_push",
                    "method": "webhook",
                    "title": "SBOM-event-to-Bombino",
                }
            ],
        },
    }


def main():
    with open("Makefile", "rt") as makefile:
        lines = gen_gha_matrix_jobs.read_makefile_lines(makefile)
    tree: dict[str, list[str]] = gen_gha_matrix_jobs.extract_target_dependencies(lines)

    for task, deps in tree.items():
        # in level 0, we only want base images, not other utility tasks
        if not deps:
            if not task.startswith("base-"):
                continue

        # we won't build rhel-based images because they need subscription
        if "rhel" in task:
            continue

        task_name = re.sub(r"[^-_0-9A-Za-z]", "-", task)

        dirs = gha_pr_changed_files.analyze_build_directories(task)

        print("---")
        print(
            yaml.dump(
                konflux_component(task_name, dockerfile_path=dirs[-1] + "/Dockerfile")
            )
        )
        # print("---")
        # print(
        #     yaml.dump(
        #         component_image_repository(task_name)
        #     )
        # )

# Using token for     quay.io/redhat-user-workloads/rhoai-ide-konflux-tenant/rhoai-ide-konflux-notebooks-jupyter-minimal-ubi9-python-311
# Token not found for quay.io/redhat-user-workloads/rhoai-ide-konflux-tenant/codeserver-ubi9-python-3-11

if __name__ == "__main__":
    main()
