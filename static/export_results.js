function downloadResultsImage() {
    var button = document.getElementById('btn_export_img');
    setExportButtonText(button, 'Building image...');

    try {
        var data = collectResultExportData();
        var canvas = drawResultExport(data);
        var link = document.createElement('a');
        link.download = 'enhanced-kinklist-' + safeFilenamePart(window.token || 'results') + '.png';
        link.href = canvas.toDataURL('image/png');
        link.click();
        setExportButtonText(button, 'Downloaded!');
    } catch (error) {
        console.error(error);
        setExportButtonText(button, 'Export failed');
    }

    setTimeout(function() {
        setExportButtonText(button, 'Download result image');
    }, 3000);
}

function collectResultExportData() {
    return {
        title: 'Enhanced Kinklist Results',
        url: window.location.origin + '/' + (window.token || ''),
        meta: Array.from(document.querySelectorAll('.meta .kinkl')).map(function(label) {
            return cleanText(label.textContent);
        }),
        legend: Array.from(document.querySelectorAll('#choices_container > div')).map(function(row) {
            return {
                color: colorFromElement(row.querySelector('.choice')),
                label: cleanText(row.querySelector('label').textContent)
            };
        }),
        groups: Array.from(document.querySelectorAll('#results_container .kink_group')).map(function(group) {
            return {
                name: cleanText(group.querySelector('.kink_header').textContent),
                columns: cleanText(group.querySelector('.kink_desc').textContent),
                rows: Array.from(group.querySelectorAll('.kink_row')).map(function(row) {
                    return {
                        label: cleanText(row.querySelector('.kink').textContent),
                        choices: Array.from(row.querySelectorAll('.choice')).map(function(choice) {
                            return colorFromElement(choice);
                        })
                    };
                })
            };
        })
    };
}

function drawResultExport(data) {
    var width = 1400;
    var margin = 42;
    var markerSize = 14;
    var rowHeight = 28;
    var groupGap = 26;
    var y = margin;
    var rows = data.groups.reduce(function(count, group) {
        return count + group.rows.length;
    }, 0);
    var height = Math.min(32000, 390 + rows * rowHeight + data.groups.length * 54);

    var canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    var ctx = canvas.getContext('2d');

    ctx.fillStyle = '#f6f7fb';
    ctx.fillRect(0, 0, width, height);

    ctx.fillStyle = '#171917';
    ctx.font = 'bold 34px Verdana, sans-serif';
    ctx.fillText(data.title, margin, y);
    y += 34;

    ctx.font = '15px Verdana, sans-serif';
    ctx.fillStyle = '#50545c';
    ctx.fillText(data.url, margin, y);
    y += 34;

    ctx.font = '16px Verdana, sans-serif';
    data.meta.forEach(function(item, index) {
        var x = margin + (index % 3) * 410;
        var metaY = y + Math.floor(index / 3) * 24;
        ctx.fillText(item, x, metaY);
    });
    y += Math.ceil(data.meta.length / 3) * 24 + 22;

    drawLegend(ctx, data.legend, margin, y);
    y += Math.ceil(data.legend.length / 2) * 24 + 34;

    data.groups.forEach(function(group) {
        if (y > height - 80) {
            return;
        }

        ctx.fillStyle = '#e9ebf2';
        ctx.fillRect(margin - 10, y - 22, width - margin * 2 + 20, 36);
        ctx.fillStyle = '#171917';
        ctx.font = 'bold 20px Verdana, sans-serif';
        ctx.fillText(group.name, margin, y);
        ctx.font = '13px Verdana, sans-serif';
        ctx.fillStyle = '#686c75';
        ctx.fillText(group.columns, margin + 360, y);
        y += groupGap;

        ctx.font = '16px Verdana, sans-serif';
        group.rows.forEach(function(row) {
            if (y > height - margin) {
                return;
            }

            row.choices.forEach(function(color, index) {
                drawMarker(ctx, margin + index * 24, y - 5, markerSize, color);
            });
            ctx.fillStyle = '#171917';
            ctx.fillText(truncateText(ctx, row.label, width - margin * 2 - 140), margin + 116, y);
            y += rowHeight;
        });
        y += 10;
    });

    return canvas;
}

function drawLegend(ctx, legend, x, y) {
    ctx.font = '14px Verdana, sans-serif';
    legend.forEach(function(item, index) {
        var col = index % 2;
        var row = Math.floor(index / 2);
        var lx = x + col * 540;
        var ly = y + row * 24;
        drawMarker(ctx, lx, ly - 5, 12, item.color);
        ctx.fillStyle = '#171917';
        ctx.fillText(item.label, lx + 22, ly);
    });
}

function drawMarker(ctx, x, y, size, color) {
    ctx.beginPath();
    ctx.arc(x + size / 2, y, size / 2, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.strokeStyle = '#222';
    ctx.lineWidth = 1;
    ctx.stroke();
}

function truncateText(ctx, text, maxWidth) {
    if (ctx.measureText(text).width <= maxWidth) {
        return text;
    }

    var result = text;
    while (result.length > 0 && ctx.measureText(result + '...').width > maxWidth) {
        result = result.slice(0, -1);
    }
    return result + '...';
}

function colorFromElement(element) {
    return element ? window.getComputedStyle(element).backgroundColor : '#d1d1d1';
}

function cleanText(text) {
    return String(text || '').replace(/\s+/g, ' ').trim();
}

function safeFilenamePart(value) {
    return String(value || 'results').replace(/[^a-z0-9_-]/gi, '_').slice(0, 48);
}

function setExportButtonText(button, text) {
    if (button) {
        button.innerText = text;
    }
}
