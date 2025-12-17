// Learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom'
import { TextDecoder, TextEncoder } from 'util'

// Mock environment variables
process.env.NEXT_PUBLIC_API_BASE_URL = 'http://localhost:8000'
process.env.NEXT_PUBLIC_API_KEY = 'test_api_key'
process.env.NODE_ENV = 'test'

// Polyfills required by some deps (e.g. jose via livekit-client) in Jest/jsdom
if (!global.TextEncoder) {
  // @ts-ignore
  global.TextEncoder = TextEncoder
}
if (!global.TextDecoder) {
  // @ts-ignore
  global.TextDecoder = TextDecoder
}

// Polyfill ResizeObserver (used by @xyflow/react / reactflow in Jest/jsdom)
if (typeof global.ResizeObserver === 'undefined') {
  // Minimal noop implementation sufficient for layout-observer deps in tests
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  global.ResizeObserver = class ResizeObserver {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    constructor(_cb) {}
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}

// Suppress console.error in tests to reduce noise (console.log is handled by component NODE_ENV check)
// Tests that need to verify logging can override with jest.spyOn
const originalError = console.error

beforeAll(() => {
  // Suppress console.error globally in tests
  console.error = jest.fn()
})

afterAll(() => {
  console.error = originalError
})
