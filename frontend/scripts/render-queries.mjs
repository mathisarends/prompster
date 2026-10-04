import ts from "typescript";

// These GET endpoints start an OAuth flow and must not be cached as reads.
const effectfulGets = new Set(["googleLogin", "spotifyLogin", "spotifyConnect"]);

function operationInputs(source) {
  const sourceFile = ts.createSourceFile("api.ts", source, ts.ScriptTarget.Latest, true);
  const inputs = new Map();

  for (const statement of sourceFile.statements) {
    if (!ts.isVariableStatement(statement)) {
      continue;
    }
    if (statement.declarationList.declarations.length !== 1) {
      throw new Error("Unexpected generated API declaration");
    }

    const declaration = statement.declarationList.declarations[0];
    const name = declaration.name.getText(sourceFile);
    const arrow = declaration.initializer;
    if (!ts.isArrowFunction(arrow)) {
      throw new Error(`Unexpected generated API operation: ${name}`);
    }

    const parameters = arrow.parameters;
    const options = parameters.at(-1);
    if (!options || options.name.getText(sourceFile) !== "options" || !options.questionToken) {
      throw new Error(`Missing request options in generated API operation: ${name}`);
    }

    inputs.set(
      name,
      parameters.slice(0, -1).map((parameter, index) => ({
        name: parameter.name.getText(sourceFile),
        optional: Boolean(parameter.questionToken),
        type: `Parameters<typeof ${name}>[${index}]`,
      })),
    );
  }

  return inputs;
}

function functionParameters(inputs) {
  return inputs
    .map(({ name, optional, type }) => `${name}${optional ? "?" : ""}: ${type}`)
    .join(", ");
}

function renderQuery(tag, name, inputs) {
  const key = [
    JSON.stringify(tag),
    JSON.stringify(name),
    ...inputs.map(({ name: inputName, optional }) =>
      optional ? `${inputName} ?? null` : inputName,
    ),
  ];
  const call = [...inputs.map(({ name: inputName }) => inputName), "{ signal }"];

  return `export const ${name}Query = (${functionParameters(inputs)}) =>
    queryOptions({
      queryKey: [${key.join(", ")}] as const,
      queryFn: ({ signal }) => ${name}(${call.join(", ")}),
    });`;
}

function renderMutation(tag, name, inputs) {
  const variables =
    inputs.length === 0
      ? ""
      : inputs.length === 1
        ? `variables: ${inputs[0].type}`
        : `variables: [${inputs.map(({ type }) => type).join(", ")}]`;
  const call = [
    ...inputs.map((_, index) => (inputs.length === 1 ? "variables" : `variables[${index}]`)),
  ];

  return `export const ${name}Mutation = () =>
    mutationOptions({
      mutationKey: [${JSON.stringify(tag)}, ${JSON.stringify(name)}] as const,
      mutationFn: (${variables}) => ${name}(${call.join(", ")}),
    });`;
}

export function renderQueryFiles(tag, operations, apiSource, header) {
  const inputs = operationInputs(apiSource);
  const queryNames = [];
  const mutationNames = [];

  for (const [name, operation] of operations) {
    if (!inputs.has(name)) {
      throw new Error(`Missing generated API operation: ${name}`);
    }
    if (operation.method === "get" && !effectfulGets.has(name)) {
      queryNames.push(name);
    } else {
      mutationNames.push(name);
    }
  }
  if (inputs.size !== operations.size) {
    throw new Error(`Unexpected generated operation for ${tag}`);
  }

  const queries = queryNames.length
    ? [
        header,
        'import { queryOptions } from "@tanstack/lit-query";',
        `import { ${queryNames.join(", ")} } from "./api";`,
        ...queryNames.map((name) => renderQuery(tag, name, inputs.get(name))),
        "",
      ].join("\n\n")
    : null;

  const mutations = mutationNames.length
    ? [
        header,
        'import { mutationOptions } from "@tanstack/lit-query";',
        `import { ${mutationNames.join(", ")} } from "./api";`,
        ...mutationNames.map((name) => renderMutation(tag, name, inputs.get(name))),
        "",
      ].join("\n\n")
    : null;

  return { queries, mutations };
}
