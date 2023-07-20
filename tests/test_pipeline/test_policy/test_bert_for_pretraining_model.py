import pytest
import torch
import torch.distributed as dist
from transformers.models.bert import BertConfig
from transformers.models.bert.modeling_bert import BertForPreTraining

import colossalai
from colossalai.cluster import ProcessGroupMesh
from colossalai.pipeline.stage_manager import PipelineStageManager
from colossalai.shardformer.policies.base_policy import Policy
from colossalai.shardformer.policies.bert import BertForPreTrainingPolicy
from colossalai.shardformer.shard import ShardConfig
from colossalai.testing import rerun_if_address_is_in_use, spawn


def check_bert_for_pretraining_policy():
    configuration = BertConfig()
    model = BertForPreTraining(configuration)
    DP_DIM, PP_DIM = 0, 1
    DP_SIZE, PP_SIZE = 2, 2
    RANK_TO_COORDINATE = {
        0: (0, 0),
        1: (0, 1),
        2: (1, 0),
        3: (1, 1),
    }
    PP_RANKS_IN_GROUP = {
        0: [0, 1],
        1: [0, 1],
        2: [2, 3],
        3: [2, 3],
    }
    pg_mesh = ProcessGroupMesh(DP_SIZE, PP_SIZE)
    # print(pg_mesh)

    stage_manager = PipelineStageManager(pg_mesh, PP_DIM)
    rank = dist.get_rank()

    model_policy = BertForPreTrainingPolicy()
    model_policy.set_model(model)

    model_config = ShardConfig(pipeline_stage_manager=stage_manager, enable_tensor_parallelism=False)
    model_policy.set_shard_config(model_config)
    layers = model_policy.get_held_layers()
    if stage_manager.is_first_stage():
        assert len(layers) == 6 + 1
    else:
        assert len(layers) == 6 + 2


def run_dist_policy(rank, world_size, port):
    colossalai.launch(config={}, rank=rank, world_size=world_size, port=port, host='localhost')
    check_bert_for_pretraining_policy()


@pytest.mark.dist
@rerun_if_address_is_in_use()
def test_bert_for_pretraining_policy():
    spawn(run_dist_policy, 4)


if __name__ == "__main__":
    """test the bert for pretraining model forward and bert for pretraining model policy"""
    test_bert_for_pretraining_policy()