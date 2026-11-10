// Division by competence (pattern 7), loaded after FrameX's competence.fx.
//
// A delay check counts as decided only when the policy derived a status
// (47-refund-policy.fx). Under the open world everything else, whatever the
// reason, is handed on to a person with the model's assessment as a note.
assessPrompt:Prompt[text -> "You help a customer service officer review a rail refund case that the rules could not decide. Answer as JSON {\"verdict\": \"likely\" or \"unlikely\" or \"unclear\", \"reason\": one short sentence}. Your assessment is only a note for the officer and decides nothing."].

?Y[cp#decided -> true] <- ?Y:DelayCheck[refundStatus -> ?S].
