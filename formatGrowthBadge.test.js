const fs = require('fs');
const path = require('path');
const vm = require('vm');

// Read app.js
const appJsPath = path.join(__dirname, 'app.js');
const appJsCode = fs.readFileSync(appJsPath, 'utf8');

// Create a script from the file content
const script = new vm.Script(appJsCode);

// Create a context (global object) for the script to run in
// We provide dummy implementations for things app.js might expect in browser environment
const sandbox = {
    document: {
        addEventListener: jest.fn(),
        querySelectorAll: jest.fn(() => []),
        getElementById: jest.fn(() => ({ style: {}, classList: { add: jest.fn(), remove: jest.fn(), toggle: jest.fn() } }))
    },
    window: {
        location: { hash: '' }
    },
    Math: Math,
    parseFloat: parseFloat,
    isNaN: isNaN,
    console: console,
    fetch: jest.fn(),
    Chart: jest.fn(),
};

vm.createContext(sandbox);

// Run the script in the context to populate it with functions from app.js
script.runInContext(sandbox);

// Get the specific function we want to test
const formatGrowthBadge = sandbox.formatGrowthBadge;

describe('formatGrowthBadge', () => {
    test('should handle falsy values for inline style', () => {
        expect(formatGrowthBadge(null, 'inline')).toBe('');
        expect(formatGrowthBadge(undefined, 'inline')).toBe('');
        expect(formatGrowthBadge('', 'inline')).toBe('');
    });

    test('should handle falsy values for table style', () => {
        expect(formatGrowthBadge(null, 'table')).toBe('<span style="color: var(--text-muted);">—</span>');
        expect(formatGrowthBadge(undefined, 'table')).toBe('<span style="color: var(--text-muted);">—</span>');
        expect(formatGrowthBadge('', 'table')).toBe('<span style="color: var(--text-muted);">—</span>');
    });

    test('should handle invalid numbers for inline style', () => {
        expect(formatGrowthBadge('N/A', 'inline')).toBe('');
        expect(formatGrowthBadge('invalid', 'inline')).toBe('');
    });

    test('should handle invalid numbers for table style', () => {
        expect(formatGrowthBadge('N/A', 'table')).toBe('<span style="color: var(--text-muted);">—</span>');
        expect(formatGrowthBadge('invalid', 'table')).toBe('<span style="color: var(--text-muted);">—</span>');
    });

    test('should format positive growth correctly inline', () => {
        const result = formatGrowthBadge('+15.5%', 'inline');
        expect(result).toContain('+15.5% YoY');
        expect(result).toContain('🔥');
        expect(result).toContain('#34d399'); // Green color
    });

    test('should format positive growth correctly in table', () => {
        const result = formatGrowthBadge('15.5%', 'table');
        expect(result).toContain('+15.5% YoY');
        expect(result).toContain('🔥');
        expect(result).toContain('#34d399');
        expect(result).toContain('font-weight: 700');
    });

    test('should format negative growth correctly inline', () => {
        const result = formatGrowthBadge('-10.2%', 'inline');
        expect(result).toContain('-10.2% YoY');
        expect(result).toContain('📉');
        expect(result).toContain('#f87171'); // Red color
    });

    test('should format negative growth correctly in table', () => {
        const result = formatGrowthBadge('-10.2%', 'table');
        expect(result).toContain('-10.2% YoY');
        expect(result).toContain('📉');
        expect(result).toContain('#f87171');
    });

    test('should format zero growth correctly inline', () => {
        const result = formatGrowthBadge('0.0%', 'inline');
        expect(result).toContain('0.0% YoY');
        expect(result).toContain('#cbd5e1'); // Gray color
    });

    test('should format zero growth correctly in table', () => {
        const result = formatGrowthBadge('0%', 'table');
        expect(result).toContain('0.0% YoY');
        expect(result).toContain('#cbd5e1');
    });

    test('should format small numbers correctly', () => {
        const result = formatGrowthBadge('0.01%', 'inline');
        expect(result).toContain('+0.0% YoY'); // Because it rounds to 1 decimal
    });
});
