/**
 * @jest-environment jsdom
 */
const { formatPotential } = require('./app.js');

describe('formatPotential', () => {
    it('returns N/A badge for missing or "N/A" input', () => {
        expect(formatPotential(null)).toBe('<span class="badge badge-neutral">N/A</span>');
        expect(formatPotential(undefined)).toBe('<span class="badge badge-neutral">N/A</span>');
        expect(formatPotential('')).toBe('<span class="badge badge-neutral">N/A</span>');
        expect(formatPotential('N/A')).toBe('<span class="badge badge-neutral">N/A</span>');
    });

    it('returns raw string for invalid percentage', () => {
        expect(formatPotential('foo')).toBe('foo');
    });

    it('formats positive percentages with green color', () => {
        expect(formatPotential('10%')).toBe('<span style="font-weight:700; color:#34d399;">+10.0%</span>');
        expect(formatPotential('10.55%')).toBe('<span style="font-weight:700; color:#34d399;">+10.6%</span>');
        expect(formatPotential('+15%')).toBe('<span style="font-weight:700; color:#34d399;">+15.0%</span>');
    });

    it('formats positive numbers with green color', () => {
        expect(formatPotential(10)).toBe('<span style="font-weight:700; color:#34d399;">+10.0%</span>');
        expect(formatPotential(10.55)).toBe('<span style="font-weight:700; color:#34d399;">+10.6%</span>');
    });

    it('formats negative percentages with red color', () => {
        expect(formatPotential('-5%')).toBe('<span style="font-weight:700; color:#f87171;">-5.0%</span>');
        expect(formatPotential('-2.34%')).toBe('<span style="font-weight:700; color:#f87171;">-2.3%</span>');
    });

    it('formats zero percentage with neutral color', () => {
        expect(formatPotential('0%')).toBe('<span style="font-weight:700; color:#cbd5e1;">0.0%</span>');
        expect(formatPotential('0.0%')).toBe('<span style="font-weight:700; color:#cbd5e1;">0.0%</span>');
        expect(formatPotential(0)).toBe('<span style="font-weight:700; color:#cbd5e1;">0.0%</span>');
    });
});
