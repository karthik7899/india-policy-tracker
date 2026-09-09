/**
 * @jest-environment jsdom
 */
const { formatPotential } = require('./app.js');

describe('formatPotential', () => {
    it('returns N/A badge for missing or "N/A" input', () => {
        expect(formatPotential(null)).toBe('—');
        expect(formatPotential(undefined)).toBe('—');
        expect(formatPotential('')).toBe('—');
        expect(formatPotential('N/A')).toBe('N/A');
    });

    it('returns raw string for invalid percentage', () => {
        expect(formatPotential('foo')).toBe('foo');
    });

    it('formats positive percentages with green color', () => {
        expect(formatPotential('10%')).toBe('<span style="font-weight:700; color:var(--success);">+10.0%</span>');
        expect(formatPotential('10.55%')).toBe('<span style="font-weight:700; color:var(--success);">+10.6%</span>');
        expect(formatPotential('+15%')).toBe('<span style="font-weight:700; color:var(--success);">+15.0%</span>');
    });

    it('formats positive numbers with green color', () => {
        expect(formatPotential(10)).toBe('<span style="font-weight:700; color:var(--success);">+10.0%</span>');
        expect(formatPotential(10.55)).toBe('<span style="font-weight:700; color:var(--success);">+10.6%</span>');
    });

    it('formats negative percentages with red color', () => {
        expect(formatPotential('-5%')).toBe('<span style="font-weight:700; color:var(--danger);">-5.0%</span>');
        expect(formatPotential('-2.34%')).toBe('<span style="font-weight:700; color:var(--danger);">-2.3%</span>');
    });

    it('formats zero percentage with neutral color', () => {
        expect(formatPotential('0%')).toBe('<span style="font-weight:700; color:var(--text-primary);">0.0%</span>');
        expect(formatPotential('0.0%')).toBe('<span style="font-weight:700; color:var(--text-primary);">0.0%</span>');
        expect(formatPotential(0)).toBe('<span style="font-weight:700; color:var(--text-primary);">0.0%</span>');
    });
});
