#!/usr/bin/env python3
"""
Deploy NVIDIA NIM endpoints on Amazon SageMaker JumpStart.

This script satisfies the NVIDIA x AWS hackathon requirement by provisioning:
1. Llama-3.1-Nemotron-Nano-8B-v1 reasoning NIM
2. Llama3-2 NV EmbedQA 1B v2 retrieval embedding NIM

It automatically retrieves the latest JumpStart model versions so you don't
have to update the script when NVIDIA refreshes the catalogue.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

import boto3
from botocore.exceptions import ClientError
import sagemaker
from sagemaker import image_uris, model_uris
from sagemaker.jumpstart.utils import get_model_specs


NEMOTRON_MODEL_ID = "nvidia-nemotron-nano-8b-nim"
EMBED_MODEL_ID = "nvidia-llama3-2-nv-embedqa-1b-v2-nim"

LLM_INSTANCE = os.getenv("NIM_LLM_INSTANCE_TYPE", "ml.g5.2xlarge")
EMBED_INSTANCE = os.getenv("NIM_EMBED_INSTANCE_TYPE", "ml.g5.xlarge")

DEFAULT_EXECUTION_ROLE = "arn:aws:iam::112571254920:role/voclabs"
EXECUTION_ROLE = os.getenv("SAGEMAKER_EXECUTION_ROLE", DEFAULT_EXECUTION_ROLE)


@dataclass
class EndpointInfo:
    model_id: str
    model_version: str
    endpoint_name: str
    instance_type: str
    region: str

    @property
    def endpoint_url(self) -> str:
        return (
            f"https://runtime.sagemaker.{self.region}.amazonaws.com/"
            f"endpoints/{self.endpoint_name}/invocations"
        )


def resolve_model_version(model_id: str, region: str) -> str:
    """Ask JumpStart which version should be used for this model id."""
    specs = get_model_specs(model_id=model_id, region=region)
    return specs.model_version


def deploy_model(
    sess: sagemaker.Session,
    model_id: str,
    model_version: str,
    instance_type: str,
    endpoint_prefix: str,
) -> Optional[EndpointInfo]:
    """Deploy a JumpStart NIM model and return endpoint metadata."""
    region = sess.boto_region_name
    endpoint_name = f"{endpoint_prefix}-{model_id}-{model_version}".replace("_", "-")
    endpoint_name = endpoint_name[:63]  # AWS endpoint name limit

    print(f"\n📦 Deploying {model_id}:{model_version}")
    print(f"   Endpoint: {endpoint_name}")
    print(f"   Instance type: {instance_type}")

    try:
        model_uri = model_uris.retrieve(
            model_id=model_id,
            model_version=model_version,
            model_scope="inference",
            region=region,
        )

        image_uri = image_uris.retrieve(
            framework=None,
            model_id=model_id,
            model_version=model_version,
            image_scope="inference",
            model_scope="inference",
            region=region,
        )

        model = sagemaker.model.Model(
            image_uri=image_uri,
            model_data=model_uri,
            role=EXECUTION_ROLE,
            sagemaker_session=sess,
        )

        predictor = model.deploy(
            initial_instance_count=1,
            instance_type=instance_type,
            endpoint_name=endpoint_name,
            wait=True,
        )

        print(f"✅ Deployed endpoint: {endpoint_name}")
        predictor.delete_model()  # endpoint keeps running, model artifact not needed locally

        return EndpointInfo(
            model_id=model_id,
            model_version=model_version,
            endpoint_name=endpoint_name,
            instance_type=instance_type,
            region=region,
        )

    except ClientError as error:
        print(f"❌ AWS error deploying {model_id}: {error}")
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Unexpected error deploying {model_id}: {exc}")

    return None


def main() -> None:
    session = sagemaker.Session()
    region = session.boto_region_name

    print("=" * 72)
    print("NVIDIA NIM Deployment for NVIDIA x AWS Hackathon")
    print("=" * 72)
    print(f"Region: {region}")
    if EXECUTION_ROLE:
        print(f"Execution role: {EXECUTION_ROLE}")
    else:
        print("Execution role: using environment defaults (SageMaker managed)")

    print("\n🔍 Resolving latest model versions from JumpStart...")
    llm_version = resolve_model_version(NEMOTRON_MODEL_ID, region)
    embed_version = resolve_model_version(EMBED_MODEL_ID, region)
    print(f"   {NEMOTRON_MODEL_ID} → v{llm_version}")
    print(f"   {EMBED_MODEL_ID} → v{embed_version}")

    endpoints: list[EndpointInfo] = []

    llm_endpoint = deploy_model(
        session,
        model_id=NEMOTRON_MODEL_ID,
        model_version=llm_version,
        instance_type=LLM_INSTANCE,
        endpoint_prefix="mindbridge-llm",
    )
    if llm_endpoint:
        endpoints.append(llm_endpoint)

    embed_endpoint = deploy_model(
        session,
        model_id=EMBED_MODEL_ID,
        model_version=embed_version,
        instance_type=EMBED_INSTANCE,
        endpoint_prefix="mindbridge-embed",
    )
    if embed_endpoint:
        endpoints.append(embed_endpoint)

    if not endpoints:
        print("\n❌ Deployment failed. Check the errors above.")
        return

    summary_path = os.path.join(os.getcwd(), "nim_endpoints.json")
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump([endpoint.__dict__ for endpoint in endpoints], handle, indent=2)

    print("\n✅ Deployment summary written to nim_endpoints.json")
    for endpoint in endpoints:
        print(
            f" - {endpoint.model_id}@{endpoint.model_version} → "
            f"{endpoint.endpoint_name} ({endpoint.endpoint_url})"
        )


if __name__ == "__main__":
    main()
