import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router';
import sample from './overview.sample.json';
import i18n from '../i18n';
import type { OverviewData } from '../lib/types';
import { OverviewView } from '../pages/Overview';

const data = sample as OverviewData;
const NOW = new Date('2026-01-02T00:00:00Z');

function renderOverview() {
  return render(
    <MemoryRouter>
      <OverviewView data={data} now={NOW} />
    </MemoryRouter>,
  );
}

describe('Overview', () => {
  beforeEach(() => i18n.changeLanguage('en'));
  afterEach(cleanup);

  it('renders in English with a decimal point', async () => {
    await i18n.changeLanguage('en');
    renderOverview();
    expect(screen.getByText('Brazil')).toBeTruthy();
    expect(screen.getByText('1.23%')).toBeTruthy();
    expect(screen.getByText('Below target band')).toBeTruthy();
    expect(screen.getByRole('note').textContent).toMatch(/not real figures/);
  });

  it('renders in Portuguese with a decimal comma', async () => {
    await i18n.changeLanguage('pt-BR');
    renderOverview();
    expect(screen.getByText('Brasil')).toBeTruthy();
    expect(screen.getByText('1,23%')).toBeTruthy();
    expect(screen.getByText('Abaixo do intervalo da meta')).toBeTruthy();
  });
});
