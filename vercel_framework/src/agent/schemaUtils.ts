/**
 * Helpers that translate Zod schemas into JSON metadata suitable for the
 * OpenRouter tool definition payloads.
 */
import { z } from "zod";

export function zodToJson(schema: z.ZodTypeAny) {
  const jsonSchema = schemaToOpenAPI(schema);
  return {
    type: "object",
    ...jsonSchema,
  };
}

export function schemaToOpenAPI(schema: z.ZodTypeAny): Record<string, unknown> {
  if (schema instanceof z.ZodObject) {
    const shape = schema.shape;
    const properties: Record<string, unknown> = {};
    const required: string[] = [];
    for (const [key, rawSchema] of Object.entries(shape) as Array<
      [string, z.ZodTypeAny]
    >) {
      const value = rawSchema;
      properties[key] = schemaToOpenAPI(value);
      if (!(value.isOptional() || value.isNullable())) {
        required.push(key);
      }
    }
    return {
      type: "object",
      properties,
      ...(required.length ? { required } : {}),
    };
  }
  if (schema instanceof z.ZodString) {
    const checks = (schema as any)._def.checks ?? [];
    const enums = checks.find((check: any) => check.kind === "enum");
    return {
      type: "string",
      ...(enums ? { enum: enums.values } : {}),
    };
  }
  if (schema instanceof z.ZodBoolean) {
    return { type: "boolean" };
  }
  if (schema instanceof z.ZodNumber) {
    const def = (schema as any)._def;
    const result: Record<string, unknown> = { type: "number" };
    if (def.checks) {
      for (const check of def.checks) {
        if (check.kind === "min") {
          result.minimum = check.value;
        }
        if (check.kind === "max") {
          result.maximum = check.value;
        }
        if (check.kind === "int") {
          result.type = "integer";
        }
      }
    }
    return result;
  }
  if (schema instanceof z.ZodNullable) {
    return {
      anyOf: [schemaToOpenAPI(schema.unwrap()), { type: "null" }],
    };
  }
  if (schema instanceof z.ZodOptional) {
    return schemaToOpenAPI(schema.unwrap());
  }
  return {};
}
