import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import i18n from '../i18n';
import type { CountryData } from '../lib/types';
import { CountryView } from '../pages/Country';
import sample from './country.sample.json';

const data = sample as CountryData;

// jsdom has no canvas or ResizeObserver; the chart layer is stubbed, the page is not.
vi.mock('../components/Chart', () => ({ Chart: ({ label }: { label: string }) => <div role="img" aria-label={label} /> }));

beforeAll(() => {
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
});

function renderCountry() {
  return render(
    <MemoryRouter>
      <CountryView d={data} />
    </MemoryRouter>,
  );
}

describe('Country page', () => {
  afterEach(cleanup);

  it('renders every section in English', async () => {
    await i18n.changeLanguage('en');
    renderCountry();
    for (const heading of ['Release', 'Drivers', 'Underlying trend', 'Momentum', 'Next month', 'Policy and markets', 'History']) {
      expect(screen.getByRole('heading', { level: 2, name: heading })).toBeTruthy();
    }
    expect(screen.getByText('+1.23%')).toBeTruthy();
    expect(screen.getByText('No market expectation is published for the IPCA-15.')).toBeTruthy();
    expect(screen.getByRole('note').textContent).toMatch(/not real figures/);
  });

  it('uses decimal commas and pt-BR labels in Portuguese', async () => {
    await i18n.changeLanguage('pt-BR');
    renderCountry();
    expect(screen.getByRole('heading', { level: 2, name: 'O que puxou' })).toBeTruthy();
    expect(screen.getByText('+1,23%')).toBeTruthy();
    expect(screen.getAllByText('+0,23 p.p.').length).toBeGreaterThan(0);
  });
});
