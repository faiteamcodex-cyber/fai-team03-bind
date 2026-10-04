"""Tests for AWS SAM template.yaml structure and parameter integrity."""

from pathlib import Path
import yaml


def test_sam_template_structure():
    template_path = Path(__file__).resolve().parent.parent.parent / "template.yaml"
    assert template_path.exists(), "template.yaml must exist at project root."

    with open(template_path, "r", encoding="utf-8") as f:
        # Load standard CloudFormation yaml (ignore custom tags like !Ref, !Sub)
        class NoTagLoader(yaml.SafeLoader):
            pass

        def ignore_tags(loader, tag_suffix, node):
            if isinstance(node, yaml.ScalarNode):
                return loader.construct_scalar(node)
            elif isinstance(node, yaml.SequenceNode):
                return loader.construct_sequence(node)
            elif isinstance(node, yaml.MappingNode):
                return loader.construct_mapping(node)
            return None

        NoTagLoader.add_multi_constructor("!", ignore_tags)
        tpl = yaml.load(f, Loader=NoTagLoader)

    # Check key sections
    assert "Parameters" in tpl
    assert "Resources" in tpl
    assert "Outputs" in tpl

    # Check parameter defaults
    params = tpl["Parameters"]
    assert params["AwsRegion"]["Default"] == "ap-south-1"
    assert params["DatasetBucketName"]["Default"] == "fai-tce-team03-datasets"
    assert params["AppStateBucketName"]["Default"] == "fai-tce-team03-app-state"
    assert params["LandRecordsTableName"]["Default"] == "fai-tce-team03-land-records"

    # Check required resources
    resources = tpl["Resources"]
    assert "LandRecordsTable" in resources
    assert "BindHttpApi" in resources
    assert "BindKernelFunction" in resources
    assert resources["LandRecordsTable"]["Type"] == "AWS::DynamoDB::Table"
    assert resources["BindKernelFunction"]["Type"] == "AWS::Serverless::Function"
