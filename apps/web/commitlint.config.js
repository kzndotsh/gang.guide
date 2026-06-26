export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'scope-enum': [2, 'always', ['web', 'data', 'pipeline', 'infra', 'deps', 'ci', 'release']],
    'scope-empty': [0, 'never'],
    'header-max-length': [2, 'always', 120],
    'body-max-line-length': [0, 'always', 200],
  },
  ignores: [(message) => message.startsWith('chore(release):')],
};
