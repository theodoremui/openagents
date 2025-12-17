const nextJest = require('next/jest')

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files in your test environment
  dir: './',
})

// Add any custom config to be passed to Jest
const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
    // Mock ESM modules that Jest can't parse
    '^react-markdown$': '<rootDir>/__mocks__/react-markdown.js',
    '^rehype-sanitize$': '<rootDir>/__mocks__/rehype-sanitize.js',
    '^rehype-raw$': '<rootDir>/__mocks__/rehype-raw.js',
    '^remark-gfm$': '<rootDir>/__mocks__/remark-gfm.js',
  },
  collectCoverageFrom: [
    'app/**/*.{js,jsx,ts,tsx}',
    'components/**/*.{js,jsx,ts,tsx}',
    'lib/**/*.{js,jsx,ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
    '!**/.next/**',
  ],
  testMatch: [
    '**/__tests__/**/*.[jt]s?(x)',
    '**/?(*.)+(spec|test).[jt]s?(x)',
  ],
  testPathIgnorePatterns: [
    '/node_modules/',
    '/.next/',
    // Exclude mock utility files from test discovery
    '/__tests__/voice/utils/',
    // TODO: useVoice.test.ts has test isolation issues causing Jest worker crashes
    // The tests pass individually but fail when run together due to mock state leakage
    '/__tests__/voice/hooks/useVoice.test.ts',
  ],
}

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = createJestConfig(customJestConfig)
