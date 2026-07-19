document.addEventListener('DOMContentLoaded', function() {
    var root = document.getElementById('home_stats');
    if (!root) {
        return;
    }

    fetch('/globalStats')
        .then(function(response) {
            if (!response.ok) {
                throw new Error('Stats request failed');
            }
            return response.json();
        })
        .then(function(stats) {
            if (!stats.summary || !stats.summary.participant_count) {
                return;
            }
            renderHomeStats(root, stats);
        })
        .catch(function(error) {
            console.error(error);
        });
});

function renderHomeStats(root, stats) {
    var summary = stats.summary;

    root.classList.remove('hidden');
    root.innerHTML = '';
    root.appendChild(element('h3', 'Community stats', 'home-stats-title'));

    var summaryGrid = element('div', '', 'home-stats-grid');
    summaryGrid.appendChild(summaryItem('Saved results', formatNumber(summary.result_count)));
    summaryGrid.appendChild(summaryItem('Participants', formatNumber(summary.participant_count)));
    summaryGrid.appendChild(summaryItem('Avg. completion', summary.average_completion_rate + '%'));
    root.appendChild(summaryGrid);

    var topGrid = element('div', '', 'home-top-grid');
    topGrid.appendChild(topList('Most favorited', stats.top.favorites));
    topGrid.appendChild(topList('Most wanted', stats.top.want_to_try));
    topGrid.appendChild(topList('Firmest limits', stats.top.hard_limits));
    root.appendChild(topGrid);

    if (stats.generated_at) {
        var updated = new Date(stats.generated_at * 1000);
        root.appendChild(element('span', 'Updated ' + updated.toLocaleString(), 'home-stats-updated'));
    }
}

function summaryItem(label, value) {
    var item = element('div', '', 'home-stat-item');
    item.appendChild(element('span', value, 'home-stat-value'));
    item.appendChild(element('span', label, 'home-stat-label'));
    return item;
}

function topList(title, rows) {
    var section = element('div', '', 'home-top-section');
    section.appendChild(element('h4', title, 'home-top-title'));

    var list = element('ol', '', 'home-top-list');
    if (!rows || rows.length === 0) {
        var empty = element('li', 'Not enough data yet', '');
        list.appendChild(empty);
    } else {
        rows.slice(0, 3).forEach(function(row) {
            var text = row.name;
            if (row.column && row.column !== 'Partner') {
                text += ' (' + row.column + ')';
            }
            text += ' - ' + row.percent + '%';
            list.appendChild(element('li', text, ''));
        });
    }

    section.appendChild(list);
    return section;
}

function element(tag, text, className) {
    var el = document.createElement(tag);
    if (className) {
        el.className = className;
    }
    el.textContent = text;
    return el;
}

function formatNumber(value) {
    return Number(value || 0).toLocaleString();
}
