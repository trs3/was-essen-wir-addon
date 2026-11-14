type Dish = {id: number; name: string; cooked_count: number; last_cooked: string|null; active: boolean};

export function CookingStats({dishes, categories, total}: {
  dishes: Dish[];
  categories: {category: string; count: number}[];
  total: number;
}) {
  const categoryCharts = [...categories].sort((a, b) => b.count - a.count || a.category.localeCompare(b.category, 'de'));
  const topDishes = dishes.filter(dish => dish.cooked_count > 0)
    .sort((a, b) => b.cooked_count - a.cooked_count || a.name.localeCompare(b.name, 'de')).slice(0, 5);
  const rediscover = dishes.filter(dish => dish.active)
    .sort((a, b) => (a.last_cooked || '').localeCompare(b.last_cooked || '') || a.name.localeCompare(b.name, 'de')).slice(0, 5);

  return <section className="card cooking-stats">
    <div className="section-title"><h3>Statistiken</h3><span className="stats-total">{total}× gekocht</span></div>
    <p className="stats-caption">Eure Küchencharts · nur tatsächlich gekochte Gerichte zählen.</p>
    <div className="stats-section">
      <h4>Kategoriencharts</h4>
      {categoryCharts.length ? <ol className="chart-list" role="list">
        {categoryCharts.map((entry, index) => <li className="chart-row" key={entry.category}>
          <span className="chart-rank" aria-hidden="true">{String(index + 1).padStart(2, '0')}</span>
          <div className="chart-info"><span className="chart-name">{entry.category}</span>
            <meter min={0} max={Math.max(1, total)} value={entry.count} aria-label={`${entry.category}: ${entry.count} von ${total} Kochereignissen`}/>
          </div>
          <span className="chart-count">{entry.count}×</span>
        </li>)}
      </ol> : <p>Noch keine Kochereignisse erfasst.</p>}
    </div>
    <div className="stats-section">
      <h4>Oft auf dem Tisch <span className="chart-subtitle">Top 5</span></h4>
      {topDishes.length ? <ol className="chart-list" role="list">
        {topDishes.map((dish, index) => <li className="chart-row" key={dish.id}>
          <span className="chart-rank" aria-hidden="true">{String(index + 1).padStart(2, '0')}</span>
          <span className="chart-info chart-name">{dish.name}</span><span className="chart-count">{dish.cooked_count}×</span>
        </li>)}
      </ol> : <p>Eure meistgekochten Gerichte erscheinen hier.</p>}
    </div>
    <div className="stats-section">
      <h4>Wiederentdecken</h4>
      <p className="stats-caption">Lange nicht gekocht – Zeit für ein Comeback.</p>
      {rediscover.length ? <ul className="chart-list" role="list">
        {rediscover.map(dish => <li className="chart-row" key={dish.id}>
          <span className="chart-comeback" aria-hidden="true">↺</span>
          <div className="chart-info"><span className="chart-name">{dish.name}</span>
            <small>{dish.last_cooked ? `Zuletzt am ${new Date(dish.last_cooked + 'T12:00:00').toLocaleDateString('de-DE')}` : 'Noch nie gekocht'}</small>
          </div>
        </li>)}
      </ul> : <p>Legt Gerichte an, um hier Inspiration zu finden.</p>}
    </div>
  </section>;
}
