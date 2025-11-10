package foundry.reasoner

# Allow reasoning requests only when the caller provides
# minimally sufficient context for downstream services.
#
# The request must include:
#   - a non-empty task identifier
#   - a non-empty objective description
#   - an optional learner identifier when present
#   - a difficulty label that maps to a known tier when provided
#
# We keep the policy intentionally simple so tests can exercise the
# integration path end-to-end without depending on the full production
# rule-set.

default allow := false

allowed_difficulties := {"intro", "easy", "medium", "hard", "advanced"}

allow if {
  valid_task_id
  valid_objective
  valid_learner
  valid_difficulty
}

valid_task_id if {
  some id
  id := trim_space(input.task_id)
  id != ""
}

valid_objective if {
  some objective
  objective := trim_space(input.objective)
  objective != ""
}

valid_learner if {
  not input.learner_id
}

valid_learner if {
  some learner
  learner := trim_space(input.learner_id)
  learner != ""
}

valid_difficulty if {
  not input.context.difficulty
}

valid_difficulty if {
  allowed_difficulties[input.context.difficulty]
}
