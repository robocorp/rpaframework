module.exports = {
  preset: "ts-jest/presets/js-with-ts",
  setupFiles: [
    "./setupJest.js"
  ],
  verbose: true,
  collectCoverage: true,
  clearMocks: true,
  moduleFileExtensions: [
    "js",
    "json",
    "jsx",
    "node",
    "ts",
    "tsx"
  ],
  transformIgnorePatterns: [
    "<rootDir>/node_modules/(?!@robocorp/ds)"
  ],
  testPathIgnorePatterns: [
    "<rootDir>/RPA/Dialogs/static/",
    "<rootDir>/node_modules/",
    "<rootDir>/lib/"
  ],
  transform: {
    '^.+\\.js?$': require.resolve('babel-jest')
  },
  globals: {
    "ts-jest": {
      tsconfig: "tsconfig.json"
    }
  }
}
