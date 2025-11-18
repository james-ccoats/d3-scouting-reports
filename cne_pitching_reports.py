import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.graphics.shapes import Drawing, Circle, Line, String
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.widgets.markers import makeMarker
from datetime import datetime
import os
from reportlab.platypus import Table, TableStyle, KeepInFrame
from reportlab.lib import colors



class ScoutingReportGenerator:
    def __init__(self, csv_file, conference_csv=None):
        self.df = pd.read_csv(csv_file, low_memory=False)
        self.csv_file = csv_file

        # Load conference data if provided
        self.conference_df = None
        if conference_csv and os.path.exists(conference_csv):
            self.conference_df = pd.read_csv(conference_csv, low_memory=False)
            # Filter to main stats only
            pattern = r'^\d+$'
            self.conference_df = self.conference_df[
                self.conference_df['number'].astype(str).str.match(pattern, na=False)]
            print(f"Loaded conference data with {len(self.conference_df)} pitchers")

        # Extract team name from filename
        base_name = os.path.basename(csv_file)
        team_name = base_name.split('_')[0].capitalize()
        self.output_file = f"{team_name}_Pitching_Report.pdf"

        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

    def _create_custom_styles(self):
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))

        self.styles.add(ParagraphStyle(
            name='PlayerName',
            parent=self.styles['Heading2'],
            fontSize=18,
            textColor=colors.HexColor('#c41e3a'),
            spaceAfter=10
        ))

        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=8
        ))

    def _get_main_pitcher_data(self):
        pattern = r'^\d+$'
        main_stats = self.df[self.df['number'].astype(str).str.match(pattern, na=False)]
        return main_stats

    def _calculate_percentiles(self, player_stats):
        if self.conference_df is None:
            return None

        percentiles = {}

        stats_config = {
            'era': {'lower_better': True, 'label': 'ERA', 'min_ip': 10},
            'whip': {'lower_better': True, 'label': 'WHIP', 'min_ip': 10},
            'k_perc': {'lower_better': False, 'label': 'K%', 'min_ip': 10},
            'bb_perc': {'lower_better': True, 'label': 'BB%', 'min_ip': 10},
            'BAA': {'lower_better': True, 'label': 'BAA', 'min_ip': 10},
            'ops': {'lower_better': True, 'label': 'OPS', 'min_ip': 10},
            'groundout_perc': {'lower_better': False, 'label': 'GB%', 'min_ip': 5},
        }

        for stat, config in stats_config.items():
            if stat == 'whip':
                if 'whip' not in player_stats or pd.isna(player_stats.get('whip')):
                    h = player_stats.get('h', 0)
                    bb = player_stats.get('bb', 0)
                    ip = player_stats.get('ip', 0)
                    # Convert IP
                    if ip > 0:
                        ip_float = float(ip)
                        whole = int(ip_float)
                        decimal = ip_float - whole
                        ip_numeric = whole + (decimal * 10 / 3)
                        player_value = (h + bb) / ip_numeric if ip_numeric > 0 else None
                    else:
                        player_value = None
                else:
                    player_value = float(player_stats['whip'])
            elif stat in player_stats and pd.notna(player_stats[stat]):
                player_value = float(player_stats[stat])
            else:
                continue

            if player_value is None:
                continue

            min_ip = config.get('min_ip', 10)
            qualified_pitchers = self.conference_df[self.conference_df['ip'] >= min_ip].copy()

            # Calculate WHIP for conference if needed
            if stat == 'whip':
                def calc_whip(row):
                    ip_float = float(row['ip'])
                    whole = int(ip_float)
                    decimal = ip_float - whole
                    ip_numeric = whole + (decimal * 10 / 3)
                    return (row['h'] + row['bb']) / ip_numeric if ip_numeric > 0 else None

                qualified_pitchers['whip'] = qualified_pitchers.apply(calc_whip, axis=1)

            conference_values = qualified_pitchers[stat].dropna()

            if len(conference_values) > 0:
                if config['lower_better']:
                    percentile = (conference_values <= player_value).sum() / len(conference_values) * 100
                    percentile = 100 - percentile
                else:
                    percentile = (conference_values <= player_value).sum() / len(conference_values) * 100

                percentiles[config['label']] = round(percentile)

        return percentiles

    def _create_percentile_visualization(self, percentiles):
        if not percentiles:
            return None

        bar_length = 580
        bar_start_x = 80
        bar_end_x = bar_start_x + bar_length

        drawing = Drawing(bar_end_x + 50, 35 * len(percentiles))
        y_position = drawing.height - 30

        for stat_label, percentile in percentiles.items():
            # Background line
            line = Line(bar_start_x, y_position, bar_end_x, y_position)
            line.strokeColor = colors.HexColor('#9b9b9b')
            line.strokeWidth = 2
            drawing.add(line)

            # Markers at 0, 50, 100
            for marker_pct in [0, 50, 100]:
                x_pos = bar_start_x + (marker_pct / 100) * bar_length
                circle = Circle(x_pos, y_position, 4)
                circle.fillColor = colors.HexColor('#9b9b9b')
                circle.strokeColor = colors.HexColor('#9b9b9b')
                drawing.add(circle)

            if pd.notna(percentile):
                x_pos = bar_start_x + (percentile / 100) * bar_length

                # Color gradient
                if percentile <= 50:
                    ratio = percentile / 50
                    r = int(41 + (255 - 41) * ratio)
                    g = int(82 + (255 - 82) * ratio)
                    b = int(163 + (255 - 163) * ratio)
                else:
                    ratio = (percentile - 50) / 50
                    r = int(255 - (255 - 204) * ratio)
                    g = int(255 - 255 * ratio)
                    b = int(255 - 255 * ratio)

                fill_color = colors.Color(r / 255, g / 255, b / 255)

                circle = Circle(x_pos, y_position, 12)
                circle.fillColor = fill_color
                circle.strokeColor = colors.black
                circle.strokeWidth = 1
                drawing.add(circle)

                text = String(x_pos, y_position - 3, str(int(percentile)))
                text.fontSize = 9
                text.fontName = 'Helvetica-Bold'
                text.fillColor = colors.black
                text.textAnchor = 'middle'
                drawing.add(text)

            label = String(10, y_position - 4, stat_label)
            label.fontSize = 11
            label.fontName = 'Helvetica-Oblique'
            label.fillColor = colors.black
            drawing.add(label)

            y_position -= 35
        drawing.translate(0, 15)
        return drawing

    def _calculate_team_stats(self):
        # Get main pitcher data only (exclude splits)
        main_pitchers = self._get_main_pitcher_data()

        # Convert IP from decimal format to fractional innings
        def convert_ip(ip_value):
            if pd.isna(ip_value):
                return 0
            ip_float = float(ip_value)
            whole = int(ip_float)
            decimal = ip_float - whole
            # Convert .1 = 1/3 inning, .2 = 2/3 inning
            fractional = decimal * 10 / 3
            return whole + fractional

        main_pitchers['ip_numeric'] = main_pitchers['ip'].apply(convert_ip)

        # Calculate totals
        total_er = main_pitchers['er'].sum()
        total_innings = main_pitchers['ip_numeric'].sum()
        k = main_pitchers['so'].sum()
        bf_total = main_pitchers['bf'].sum()
        bb_total = main_pitchers['bb'].sum()
        hb_total = main_pitchers['hb'].sum()
        ibb_total = main_pitchers['ibb'].sum()
        sha_total = main_pitchers['sha'].sum()
        sfa_total = main_pitchers['sfa'].sum()
        h_total = main_pitchers['h'].sum()
        x2b_total = main_pitchers['x2b_a'].sum()
        x3b_total = main_pitchers['x3b_a'].sum()
        hr_total = main_pitchers['hr_a'].sum()
        fo_total = main_pitchers['fo'].sum()
        go_total = main_pitchers['go'].sum()

        # Derived statistics
        AB = bf_total - (bb_total + hb_total + ibb_total + sha_total + sfa_total)
        BAA = h_total / AB if AB > 0 else 0
        flyout_perc = fo_total / (go_total + fo_total) if (go_total + fo_total) > 0 else 0
        groundout_perc = go_total / (go_total + fo_total) if (go_total + fo_total) > 0 else 0
        k_perc = k / bf_total if bf_total > 0 else 0
        bb_perc = bb_total / bf_total if bf_total > 0 else 0
        obp = (h_total + bb_total + hb_total) / (AB + bb_total + hb_total + sfa_total) if (
                                                                                                      AB + bb_total + hb_total + sfa_total) > 0 else 0
        x1b_a = h_total - (x2b_total + x3b_total + hr_total)
        slg = (x1b_a + 2 * x2b_total + 3 * x3b_total + 4 * hr_total) / AB if AB > 0 else 0
        ops = obp + slg
        k_bb_ratio = k / bb_total if bb_total > 0 else k
        era = (total_er * 9) / total_innings if total_innings > 0 else 0
        whip = (h_total + bb_total) / total_innings if total_innings > 0 else 0

        return {
            'era': era,
            'whip': whip,
            'ip': total_innings,
            'so': k,
            'bb': bb_total,
            'k_bb_ratio': k_bb_ratio,
            'h': h_total,
            'BAA': BAA,
            'ops': ops,
            'k_perc': k_perc,
            'bb_perc': bb_perc,
        }

    def _create_team_comparison_chart(self, team_stats, stat_name, label):
        if self.conference_df is None:
            return None

        # Calculate conference team stats
        conference_teams = self.conference_df['team_id'].unique()
        conference_team_stats = []

        for team in conference_teams:
            team_pitchers = self.conference_df[self.conference_df['team_id'] == team]

            # Same calculation logic
            def convert_ip(ip_value):
                if pd.isna(ip_value):
                    return 0
                ip_float = float(ip_value)
                whole = int(ip_float)
                decimal = ip_float - whole
                fractional = decimal * 10 / 3
                return whole + fractional

            team_pitchers['ip_numeric'] = team_pitchers['ip'].apply(convert_ip)

            if stat_name == 'era':
                total_er = team_pitchers['er'].sum()
                total_innings = team_pitchers['ip_numeric'].sum()
                value = (total_er * 9) / total_innings if total_innings > 0 else 0
            elif stat_name == 'k_bb_diff':
                k = team_pitchers['so'].sum()
                bf_total = team_pitchers['bf'].sum()
                bb_total = team_pitchers['bb'].sum()
                k_perc = k / bf_total if bf_total > 0 else 0
                bb_perc = bb_total / bf_total if bf_total > 0 else 0
                value = k_perc - bb_perc

            conference_team_stats.append(value)

        # Create drawing
        drawing = Drawing(450, 100)

        # Sort values for ranking
        sorted_values = sorted(conference_team_stats)
        team_value = team_stats['era'] if stat_name == 'era' else (team_stats['k_perc'] - team_stats['bb_perc'])

        # Find team's rank
        if stat_name == 'era':
            rank = sum(1 for v in sorted_values if v < team_value) + 1
        else:
            rank = sum(1 for v in sorted_values if v > team_value) + 1

        # Draw background line
        line = Line(50, 50, 400, 50)
        line.strokeColor = colors.HexColor('#cccccc')
        line.strokeWidth = 3
        drawing.add(line)

        # Draw all conference teams as small dots
        for val in sorted_values:
            if stat_name == 'era':
                min_val, max_val = min(sorted_values), max(sorted_values)
            else:
                min_val, max_val = min(sorted_values), max(sorted_values)

            if max_val > min_val:
                if stat_name == 'era':
                    x_pos = 50 + ((max_val - val) / (max_val - min_val)) * 350
                else:
                    x_pos = 50 + ((val - min_val) / (max_val - min_val)) * 350
            else:
                x_pos = 225

            circle = Circle(x_pos, 50, 3)
            circle.fillColor = colors.HexColor('#cccccc')
            circle.strokeColor = colors.HexColor('#999999')
            drawing.add(circle)

        # Highlight team's position
        if max_val > min_val:
            if stat_name == 'era':
                team_x = 50 + ((max_val - team_value) / (max_val - min_val)) * 350
            else:
                team_x = 50 + ((team_value - min_val) / (max_val - min_val)) * 350
        else:
            team_x = 225

        # Color based on rank
        if rank <= len(conference_teams) * 0.25:
            team_color = colors.HexColor('#00AA00')  # Green - top 25%
        elif rank <= len(conference_teams) * 0.5:
            team_color = colors.HexColor('#FFA500')  # Orange - top 50%
        else:
            team_color = colors.HexColor('#FF0000')  # Red - bottom 50%

        circle = Circle(team_x, 50, 8)
        circle.fillColor = team_color
        circle.strokeColor = colors.black
        circle.strokeWidth = 2
        drawing.add(circle)

        # Add labels
        title = String(225, 85, label)
        title.fontSize = 12
        title.fontName = 'Helvetica-Bold'
        title.textAnchor = 'middle'
        drawing.add(title)

        # Add value and rank
        value_text = f"{team_value:.2f}" if stat_name == 'era' else f"{team_value:.1%}"
        rank_text = f"Rank: {rank}/{len(conference_teams)}"

        val_label = String(team_x, 30, value_text)
        val_label.fontSize = 10
        val_label.fontName = 'Helvetica-Bold'
        val_label.textAnchor = 'middle'
        drawing.add(val_label)

        rank_label = String(team_x, 15, rank_text)
        rank_label.fontSize = 8
        rank_label.textAnchor = 'middle'
        drawing.add(rank_label)

        # Add min/max labels
        if stat_name == 'era':
            min_label = String(400, 60, f"Best: {min_val:.2f}")
            max_label = String(50, 60, f"Worst: {max_val:.2f}")
        else:
            max_label = String(400, 60, f"Best: {max_val:.1%}")
            min_label = String(50, 60, f"Worst: {min_val:.1%}")

        min_label.fontSize = 8
        max_label.fontSize = 8
        min_label.textAnchor = 'end'
        max_label.textAnchor = 'start'
        drawing.add(min_label)
        drawing.add(max_label)

        return drawing

    def _create_summary_page(self, story):
        base_name = os.path.basename(self.csv_file)
        team_name = base_name.split('_')[0].capitalize()

        title = Paragraph("PITCHING STAFF SCOUTING REPORT", self.styles['CustomTitle'])
        story.append(title)

        year = self.df['year'].iloc[0] if 'year' in self.df.columns else datetime.now().year
        subtitle = Paragraph(f"{team_name} | Season: {year}", self.styles['Normal'])
        story.append(subtitle)
        story.append(Spacer(1, 0.3 * inch))

        # Calculate team stats properly
        team_stats = self._calculate_team_stats()

        def safe_format(value, format_str='.2f', is_percent=False, multiplier=1):
            if pd.isna(value) or value == float('inf') or value == float('-inf'):
                return "N/A"
            try:
                result = float(value) * multiplier
                if is_percent:
                    return f"{result:.1f}%"
                else:
                    return f"{result:{format_str}}"
            except (ValueError, TypeError):
                return "N/A"

        summary_data = [
            ['TEAM PITCHING SUMMARY', ''],
            ['Team ERA', safe_format(team_stats['era'], '.2f')],
            ['Team WHIP', safe_format(team_stats['whip'], '.2f')],
            ['Total Innings', safe_format(team_stats['ip'], '.1f')],
            ['Total Strikeouts', str(int(team_stats['so']))],
            ['Total Walks', str(int(team_stats['bb']))],
            ['K/BB Ratio', safe_format(team_stats['k_bb_ratio'], '.2f')],
            ['Hits Allowed', str(int(team_stats['h']))],
            ['BAA', safe_format(team_stats['BAA'], '.3f')],
            ['OPS Against', safe_format(team_stats['ops'], '.3f')],
            ['K%', safe_format(team_stats['k_perc'], is_percent=True, multiplier=100)],
            ['BB%', safe_format(team_stats['bb_perc'], is_percent=True, multiplier=100)],
        ]

        t = Table(summary_data, colWidths=[3 * inch, 2 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(t)
        story.append(Spacer(1, 0.4 * inch))

        if self.conference_df is not None:
            story.append(Paragraph("CONFERENCE RANKINGS", self.styles['SectionHeader']))
            story.append(Spacer(1, 0.2 * inch))

            # ERA chart
            era_chart = self._create_team_comparison_chart(team_stats, 'era', 'Team ERA vs Conference')
            if era_chart:
                story.append(era_chart)
                story.append(Spacer(1, 0.3 * inch))

            # K% - BB% chart
            kbb_chart = self._create_team_comparison_chart(team_stats, 'k_bb_diff', 'K% - BB% vs Conference')
            if kbb_chart:
                story.append(kbb_chart)
                story.append(Spacer(1, 0.3 * inch))

        story.append(PageBreak())



    def _create_player_page(self, player_data, story):

        import pandas as pd
        from reportlab.platypus import (
            Paragraph, Spacer, Table, TableStyle, PageBreak, KeepInFrame
        )
        from reportlab.lib import colors
        from reportlab.lib.units import inch


        pattern = r'^\d+$'
        main_row = player_data[player_data['number'].astype(str).str.match(pattern, na=False)]

        if main_row.empty:
            return

        main_row = main_row.iloc[0]

        player_name = main_row['player']
        yr = main_row['yr'] if pd.notna(main_row['yr']) else 'N/A'
        pos = main_row['pos'] if pd.notna(main_row['pos']) else 'P'
        b_t = main_row['b_t'] if pd.notna(main_row['b_t']) else 'N/A'

        story.append(Paragraph(f"{player_name} - #{main_row['number']}", self.styles['PlayerName']))
        story.append(Paragraph(f"{yr} | {pos} | {b_t}", self.styles['Normal']))
        story.append(Spacer(1, 0.15 * inch))


        primary_stats = [
            ['Stat', 'Value'],
            ['Appearances', str(int(main_row['app'])) if pd.notna(main_row['app']) else '0'],
            ['Games Started', str(int(main_row['gs'])) if pd.notna(main_row['gs']) else '0'],
            ['ERA', f"{main_row['era']:.2f}" if pd.notna(main_row['era']) else 'N/A'],
            ['Innings Pitched', str(main_row['ip']) if pd.notna(main_row['ip']) else '0'],
            ['Wins', str(int(main_row['w'])) if pd.notna(main_row['w']) else '0'],
            ['Losses', str(int(main_row['l'])) if pd.notna(main_row['l']) else '0'],
            ['Saves', str(int(main_row['sv'])) if pd.notna(main_row['sv']) else '0'],
            ['Strikeouts', str(int(main_row['so'])) if pd.notna(main_row['so']) else '0'],
            ['Walks', str(int(main_row['bb'])) if pd.notna(main_row['bb']) else '0'],
            ['K/BB Ratio',
             f"{main_row['so'] / max(main_row['bb'], 1):.2f}"
             if pd.notna(main_row['so']) and pd.notna(main_row['bb']) else 'N/A'],
            ['Hits Allowed', str(int(main_row['h'])) if pd.notna(main_row['h']) else '0'],
            ['Home Runs', str(int(main_row['hr_a'])) if pd.notna(main_row['hr_a']) else '0'],
            ['BAA', f"{main_row['BAA']:.3f}" if pd.notna(main_row['BAA']) else 'N/A'],
            ['OPS Against', f"{main_row['ops']:.3f}" if pd.notna(main_row['ops']) else 'N/A'],
            ['Ground Ball %',
             f"{main_row['groundout_perc'] * 100:.1f}%" if pd.notna(main_row['groundout_perc']) else 'N/A'],
            ['Fly Out %',
             f"{main_row['flyout_perc'] * 100:.1f}%" if pd.notna(main_row['flyout_perc']) else 'N/A'],
            ['K%', f"{main_row['k_perc'] * 100:.1f}%" if pd.notna(main_row['k_perc']) else 'N/A'],
            ['BB%', f"{main_row['bb_perc'] * 100:.1f}%" if pd.notna(main_row['bb_perc']) else 'N/A'],
        ]

        t_primary = Table(primary_stats, colWidths=[2.2 * inch, 1.0 * inch])
        t_primary.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#c41e3a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))


        pattern2 = r'^\d+$'
        situational_data = player_data[~player_data['number'].astype(str).str.match(pattern2, na=False)]

        t_situational = Paragraph("No situational data", self.styles['Normal'])

        if not situational_data.empty:
            situational_stats = [['Situation', 'IP', 'H', 'BB', 'SO', 'BAA', 'OPS']]

            for _, row in situational_data.iterrows():
                name = row['number']
                ln = name.lower()

                # display names
                mapping = {
                    'vs lhb': 'vs LHB', 'vs lh': 'vs LHB',
                    'vs rhb': 'vs RHB', 'vs rh': 'vs RHB',
                    'with runners ob': 'Runners On',
                    'scorepos2': 'RISP 2-Out',
                    'scorepos': 'RISP',
                    'runners2': 'Runners on 2nd',
                    'bases loaded': 'Bases Loaded',
                    'bases empty': 'Bases Empty',
                    'w2outs': '2 Outs',
                    'leadoff': 'vs Leadoff'
                }

                display = next((v for k, v in mapping.items() if k in ln), name[:20])

                situational_stats.append([
                    display,
                    str(row['ip']) if pd.notna(row['ip']) else '-',
                    str(int(row['h'])) if pd.notna(row['h']) else '-',
                    str(int(row['bb'])) if pd.notna(row['bb']) else '-',
                    str(int(row['so'])) if pd.notna(row['so']) else '-',
                    f"{row['BAA']:.3f}" if pd.notna(row['BAA']) else '-',
                    f"{row['ops']:.3f}" if pd.notna(row['ops']) else '-',
                ])

            t_situational = Table(
                situational_stats,
                colWidths=[1.8 * inch, 0.6 * inch, 0.5 * inch, 0.5 * inch,
                           0.5 * inch, 0.6 * inch, 0.6 * inch],
                rowHeights=[0.30 * inch] + [0.35 * inch] * (len(situational_stats) - 1)
            )
            t_situational.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ]))


        percentile_viz = None
        if self.conference_df is not None:
            percentiles = self._calculate_percentiles(main_row)
            if percentiles:
                percentile_viz = self._create_percentile_visualization(percentiles)

        if percentile_viz is None:
            percentile_viz = Paragraph("No percentile data", self.styles['Normal'])


        notes_data = [
            ['Area', 'Notes'],
            ['Strengths', ''],
            ['Weaknesses', ''],
            ['Game Plan', ''],
            ['Key Matchups', '']
        ]

        t_notes = Table(
            notes_data,
            colWidths=[1.3 * inch, 8 * inch],
            rowHeights=[0.3 * inch] + [0.75 * inch] * 4,
            hAlign = 'CENTER'
        )

        t_notes.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#c41e3a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('VALIGN', (0, 1), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))

        layout_grid = [
            [t_primary, t_situational],  # top row = 2 columns
            [percentile_viz],  # middle = 1 column full width
            [t_notes]  # bottom = 1 column full width
        ]

        layout_table = Table(layout_grid, colWidths=[3.45 * inch, 3.45 * inch])
        layout_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))

        # Fit everything on one page
        final_frame = KeepInFrame(
            7.0 * inch,
            9.1 * inch,
            [layout_table],
            mode='shrink'
        )

        story.append(final_frame)
        story.append(PageBreak())

    def generate_report(self):
        doc = SimpleDocTemplate(self.output_file, pagesize=letter,
                                rightMargin=0.5 * inch, leftMargin=0.5 * inch,
                                topMargin=0.5 * inch, bottomMargin=0.5 * inch)

        story = []

        self._create_summary_page(story)

        main_pitchers = self._get_main_pitcher_data()
        main_pitchers = main_pitchers.sort_values('ip', ascending=False)
        unique_players = main_pitchers['player'].unique()

        for player in unique_players:
            player_data = self.df[self.df['player'] == player]
            self._create_player_page(player_data, story)

        doc.build(story)
        print(f"Scouting report generated: {self.output_file}")


if __name__ == "__main__":
    generator = ScoutingReportGenerator(
        csv_file="gordon_pitching.csv",
        conference_csv="conference_all_pitchers.csv"
    )
    generator.generate_report()

    print("PDF scouting report created successfully!")
    print("\nLayout: ")
    print("- Page 1: Team summary with conference rankings")
    print("- Each player: One page with stats/situational (top), percentiles/notes (bottom)")