const fs = require('fs');
const path = require('path');
const vm = require('vm');

const appJsCode = fs.readFileSync(path.join(__dirname, '../app.js'), 'utf8');

const context = {
    document: {
        addEventListener: () => {},
        querySelectorAll: () => [],
        getElementById: () => ({ addEventListener: () => {} })
    },
    window: {
        addEventListener: () => {}
    },
    fetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
    Chart: function() { return { destroy: () => {} }; },
    module: { exports: {} }
};

vm.createContext(context);
vm.runInContext(appJsCode, context);

const formatGrowthBadge = context.formatGrowthBadge;

describe('formatGrowthBadge', () => {
    it('should return N/A badge for missing, null, undefined, or "N/A" strings', () => {
        const expected = '<span class="badge badge-neutral">N/A</span>';
        expect(formatGrowthBadge(null)).toBe(expected);
        expect(formatGrowthBadge(undefined)).toBe(expected);
        expect(formatGrowthBadge('')).toBe(expected);
        expect(formatGrowthBadge('N/A')).toBe(expected);
    });

    it('should format positive percentage growth strings', () => {
        const inlineResult = formatGrowthBadge('15.5%');
        expect(inlineResult).toContain('🔥 +15.5% YoY');
        expect(inlineResult).toContain('color: #34d399');

        const tableResult = formatGrowthBadge('+15.5%', 'table');
        expect(tableResult).toBe('<span style="font-weight: 700; color: #34d399;">🔥 +15.5% YoY</span>');
    });

    it('should format negative percentage growth strings', () => {
        const inlineResult = formatGrowthBadge('-10.2%');
        expect(inlineResult).toContain('📉 -10.2% YoY');
        expect(inlineResult).toContain('color: #f87171');

        const tableResult = formatGrowthBadge('-10.2%', 'table');
        expect(tableResult).toBe('<span style="font-weight: 700; color: #f87171;">📉 -10.2% YoY</span>');
    });

    it('should format zero growth correctly', () => {
        const inlineResult = formatGrowthBadge('0.0%');
        expect(inlineResult).toContain('0.0% YoY');
        expect(inlineResult).toContain('color: #cbd5e1');

        const tableResult = formatGrowthBadge('0%', 'table');
        expect(tableResult).toBe('<span style="font-weight: 700; color: #cbd5e1;">0.0% YoY</span>');
    });

    it('should handle numeric inputs correctly', () => {
        const posResult = formatGrowthBadge(15.5, 'table');
        expect(posResult).toBe('<span style="font-weight: 700; color: #34d399;">🔥 +15.5% YoY</span>');

        const negResult = formatGrowthBadge(-10.2, 'table');
        expect(negResult).toBe('<span style="font-weight: 700; color: #f87171;">📉 -10.2% YoY</span>');
    });

    it('should handle invalid string numbers properly', () => {
        expect(formatGrowthBadge('invalid', 'table')).toBe('<span style="color: var(--text-muted);">—</span>');
    });
});
