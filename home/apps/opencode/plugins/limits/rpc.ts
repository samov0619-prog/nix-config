// Portable JSON Schema contract; no additional runtime dependency.
export const Limits = {
  id: "local.limits",
  methods: {
    status: {
      input: { type: "object", additionalProperties: false },
      output: { type: "object", additionalProperties: true },
    },
    reset: {
      input: { type: "object", additionalProperties: false },
      output: { type: "object", additionalProperties: true },
    },
  },
  events: {
    updated: { schema: { type: "object", additionalProperties: false } },
  },
} as const;
