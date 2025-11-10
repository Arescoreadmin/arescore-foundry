package foundry_reasoner_test

import data.foundry.reasoner

valid_input := {
  "task_id": "task-123",
  "objective": "Guide learner through adaptive drill",
  "context": {"difficulty": "medium"},
  "learner_id": "learner-42",
}

test_reasoner_allows_valid_request if {
  reasoner.allow with input as valid_input
}

test_reasoner_allows_without_learner if {
  request := {
    "task_id": valid_input.task_id,
    "objective": valid_input.objective,
    "context": valid_input.context,
  }
  reasoner.allow with input as request
}

test_reasoner_denies_blank_objective if {
  not reasoner.allow with input as {
    "task_id": valid_input.task_id,
    "objective": "   ",
    "context": valid_input.context,
    "learner_id": valid_input.learner_id,
  }
}

test_reasoner_denies_unknown_difficulty if {
  not reasoner.allow with input as {
    "task_id": valid_input.task_id,
    "objective": valid_input.objective,
    "context": {"difficulty": "legendary"},
    "learner_id": valid_input.learner_id,
  }
}
