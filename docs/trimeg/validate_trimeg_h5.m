%% validate_trimeg_h5.m
% 使用卢老师提供的原始 loadfemmesh_h5.m，对比：
%   1. 标准 TRIMEG 示例 femmesh_65402_t1_nr16core.h5
%   2. LinkMesh 从服务器生成并下载的 mesh.h5
%
% 不修改 HDF5 文件，不修改 loadfemmesh_h5.m，不手动调整数据方向或索引。

clear;
clc;
close all;

%% 定位当前脚本目录

script_file = mfilename('fullpath');

if isempty(script_file)
    error('无法确定 validate_trimeg_h5.m 的完整路径。');
end

script_dir = fileparts(script_file);
loader_file = fullfile(script_dir, 'loadfemmesh_h5.m');
output_dir = fullfile(script_dir, 'validation_output');

if ~isfile(loader_file)
    error('找不到标准读取器：%s', loader_file);
end

if ~exist(output_dir, 'dir')
    mkdir(output_dir);
end

addpath(script_dir);

%% 仅验证标准示例和 LinkMesh 输出

case_names = {
    'standard_femmesh'
    'linkmesh_mesh'
};

case_files = {
    fullfile(script_dir, 'femmesh_65402_t1_nr16core.h5')
    fullfile(script_dir, 'mesh.h5')
};

for case_index = 1:numel(case_files)
    if ~isfile(case_files{case_index})
        error('找不到待验证文件：%s', case_files{case_index});
    end
end

fprintf('\n');
fprintf('============================================================\n');
fprintf('TRIMEG HDF5 MATLAB validation\n');
fprintf('标准读取器：%s\n', loader_file);
fprintf('输出目录：%s\n', output_dir);
fprintf('============================================================\n');

%% 打开汇总文件

summary_file = fullfile(output_dir, 'validation_summary.txt');
summary_id = fopen(summary_file, 'w');

if summary_id < 0
    error('无法创建汇总文件：%s', summary_file);
end

summary_cleanup = onCleanup(@() fclose(summary_id));

fprintf(summary_id, 'TRIMEG HDF5 MATLAB validation\n');
fprintf(summary_id, 'Reader: %s\n\n', loader_file);

%% 依次读取和绘图

for case_index = 1:numel(case_files)
    case_name = case_names{case_index};
    h5_file = case_files{case_index};

    fprintf('\n');
    fprintf('------------------------------------------------------------\n');
    fprintf('正在验证：%s\n', case_name);
    fprintf('文件：%s\n', h5_file);
    fprintf('------------------------------------------------------------\n');

    %% 使用卢老师的原始函数读取，不自行转置或修正索引

    femmesh = loadfemmesh_h5(h5_file, 0, 0);

    nvert = double(femmesh.nvert(1));
    ntria = double(femmesh.ntria(1));
    nvert_in = double(femmesh.nvert_in(1));
    nvert_ex = double(femmesh.nvert_ex(1));

    fprintf('nvert    = %d\n', nvert);
    fprintf('ntria    = %d\n', ntria);
    fprintf('nvert_in = %d\n', nvert_in);
    fprintf('nvert_ex = %d\n', nvert_ex);
    fprintf('size(vert) = [%d, %d]\n', ...
        size(femmesh.vert, 1), size(femmesh.vert, 2));
    fprintf('size(tria) = [%d, %d]\n', ...
        size(femmesh.tria, 1), size(femmesh.tria, 2));

    %% 检查 MATLAB 消费后的数组形状

    assert(size(femmesh.vert, 1) == nvert, ...
        '%s：vert 行数与 nvert 不一致。', case_name);

    assert(size(femmesh.vert, 2) == 2, ...
        '%s：MATLAB 读取后的 vert 必须为 N x 2。', case_name);

    assert(size(femmesh.tria, 1) == ntria, ...
        '%s：tria 行数与 ntria 不一致。', case_name);

    assert(size(femmesh.tria, 2) >= 3, ...
        '%s：MATLAB 读取后的 tria 至少需要三列。', case_name);

    assert(all(isfinite(femmesh.vert(:))), ...
        '%s：vert 含 NaN 或 Inf。', case_name);

    assert(all(isfinite(femmesh.tria(:))), ...
        '%s：tria 含 NaN 或 Inf。', case_name);

    %% 检查前三列三角形连接表

    connectivity = double(femmesh.tria(:, 1:3));

    assert(all(connectivity(:) == round(connectivity(:))), ...
        '%s：tria 前三列含非整数节点索引。', case_name);

    minimum_index = min(connectivity(:));
    maximum_index = max(connectivity(:));

    fprintf('节点索引范围 = [%d, %d]\n', ...
        minimum_index, maximum_index);

    assert(minimum_index >= 1, ...
        '%s：存在小于 1 的 MATLAB 节点索引。', case_name);

    assert(maximum_index <= nvert, ...
        '%s：节点索引越界，最大值=%d，nvert=%d。', ...
        case_name, maximum_index, nvert);

    repeated_vertex = ...
        connectivity(:, 1) == connectivity(:, 2) | ...
        connectivity(:, 2) == connectivity(:, 3) | ...
        connectivity(:, 1) == connectivity(:, 3);

    assert(~any(repeated_vertex), ...
        '%s：存在包含重复顶点的退化三角形。', case_name);

    %% 检查三角形面积

    point_1 = femmesh.vert(connectivity(:, 1), :);
    point_2 = femmesh.vert(connectivity(:, 2), :);
    point_3 = femmesh.vert(connectivity(:, 3), :);

    twice_area = ...
        (point_2(:, 1) - point_1(:, 1)) .* ...
        (point_3(:, 2) - point_1(:, 2)) - ...
        (point_3(:, 1) - point_1(:, 1)) .* ...
        (point_2(:, 2) - point_1(:, 2));

    triangle_area = 0.5 * abs(twice_area);

    fprintf('最小三角形面积 = %.16e\n', min(triangle_area));
    fprintf('最大三角形面积 = %.16e\n', max(triangle_area));

    assert(all(isfinite(triangle_area)), ...
        '%s：三角形面积含 NaN 或 Inf。', case_name);

    assert(all(triangle_area > 0), ...
        '%s：存在零面积三角形。', case_name);

    %% 检查内部和外部节点表

    idxivert = double(femmesh.idxivert(:));
    idxevert = double(femmesh.idxevert(:));

    assert(numel(idxivert) == nvert_in, ...
        '%s：idxivert 数量与 nvert_in 不一致。', case_name);

    assert(numel(idxevert) == nvert_ex, ...
        '%s：idxevert 数量与 nvert_ex 不一致。', case_name);

    assert(nvert_in + nvert_ex == nvert, ...
        '%s：nvert_in + nvert_ex 与 nvert 不一致。', case_name);

    if ~isempty(idxivert)
        assert(min(idxivert) >= 1 && max(idxivert) <= nvert, ...
            '%s：idxivert 存在越界索引。', case_name);
    end

    if ~isempty(idxevert)
        assert(min(idxevert) >= 1 && max(idxevert) <= nvert, ...
            '%s：idxevert 存在越界索引。', case_name);
    end

    %% 检查可选的 Rbc/Zbc

    has_boundary = ...
        isfield(femmesh, 'nbcRZ') && ...
        isfield(femmesh, 'Rbc') && ...
        isfield(femmesh, 'Zbc');

    boundary_count = NaN;
    boundary_area = NaN;

    if has_boundary
        boundary_count = double(femmesh.nbcRZ(1));
        boundary_r = double(femmesh.Rbc(:));
        boundary_z = double(femmesh.Zbc(:));

        fprintf('nbcRZ = %d\n', boundary_count);

        assert(numel(boundary_r) == boundary_count, ...
            '%s：Rbc 数量与 nbcRZ 不一致。', case_name);

        assert(numel(boundary_z) == boundary_count, ...
            '%s：Zbc 数量与 nbcRZ 不一致。', case_name);

        assert(boundary_count >= 3, ...
            '%s：Rbc/Zbc 点数不足 3。', case_name);

        assert(all(isfinite(boundary_r)) && all(isfinite(boundary_z)), ...
            '%s：Rbc/Zbc 含 NaN 或 Inf。', case_name);

        assert(~isequal( ...
            [boundary_r(1), boundary_z(1)], ...
            [boundary_r(end), boundary_z(end)]), ...
            '%s：Rbc/Zbc 首尾点重复。', case_name);

        boundary_area = 0.5 * sum( ...
            boundary_r .* circshift(boundary_z, -1) - ...
            circshift(boundary_r, -1) .* boundary_z ...
        );

        fprintf('Rbc/Zbc 带符号面积 = %.16e\n', boundary_area);
    else
        fprintf('该文件未提供 nbcRZ/Rbc/Zbc。\n');
    end

    %% 使用清晰的白色背景绘制网格

    figure_handle = figure( ...
        'Name', case_name, ...
        'NumberTitle', 'off', ...
        'Color', 'w', ...
        'Units', 'normalized', ...
        'Position', [0.08, 0.08, 0.42, 0.78] ...
    );

    axes_handle = axes( ...
        'Parent', figure_handle, ...
        'Color', 'w', ...
        'XColor', 'k', ...
        'YColor', 'k', ...
        'GridColor', [0.82, 0.82, 0.82], ...
        'GridAlpha', 0.45, ...
        'LineWidth', 0.8, ...
        'FontSize', 11 ...
    );

    hold(axes_handle, 'on');

    patch( ...
        'Parent', axes_handle, ...
        'Faces', connectivity, ...
        'Vertices', femmesh.vert, ...
        'FaceColor', [0.84, 0.91, 0.97], ...
        'FaceAlpha', 0.55, ...
        'EdgeColor', [0.28, 0.38, 0.48], ...
        'EdgeAlpha', 0.70, ...
        'LineWidth', 0.25 ...
    );

    if has_boundary
        plot( ...
            axes_handle, ...
            [boundary_r; boundary_r(1)], ...
            [boundary_z; boundary_z(1)], ...
            'Color', [0.85, 0.10, 0.10], ...
            'LineStyle', '-', ...
            'LineWidth', 2.0 ...
        );
    end

    axis(axes_handle, 'equal');
    grid(axes_handle, 'on');
    box(axes_handle, 'on');

    xlabel(axes_handle, 'R [m]', ...
        'Color', 'k', ...
        'FontSize', 12);

    ylabel(axes_handle, 'Z [m]', ...
        'Color', 'k', ...
        'FontSize', 12);

    title( ...
        axes_handle, ...
        sprintf('%s: %d nodes, %d triangles', ...
        strrep(case_name, '_', '\_'), nvert, ntria), ...
        'Interpreter', 'tex', ...
        'Color', 'k', ...
        'FontSize', 12 ...
    );

    drawnow;

    png_file = fullfile(output_dir, [case_name, '.png']);
    fig_file = fullfile(output_dir, [case_name, '.fig']);

    exportgraphics( ...
    figure_handle, ...
    png_file, ...
    'Resolution', 250, ...
    'BackgroundColor', 'white' ...
    );
    savefig(figure_handle, fig_file);

    fprintf('PNG 已保存：%s\n', png_file);
    fprintf('FIG 已保存：%s\n', fig_file);

    %% 写入文本汇总

    fprintf(summary_id, 'CASE: %s\n', case_name);
    fprintf(summary_id, 'FILE: %s\n', h5_file);
    fprintf(summary_id, 'nvert: %d\n', nvert);
    fprintf(summary_id, 'ntria: %d\n', ntria);
    fprintf(summary_id, 'nvert_in: %d\n', nvert_in);
    fprintf(summary_id, 'nvert_ex: %d\n', nvert_ex);
    fprintf(summary_id, 'triangle_index_min: %d\n', minimum_index);
    fprintf(summary_id, 'triangle_index_max: %d\n', maximum_index);
    fprintf(summary_id, 'minimum_triangle_area: %.16e\n', ...
        min(triangle_area));
    fprintf(summary_id, 'maximum_triangle_area: %.16e\n', ...
        max(triangle_area));
    fprintf(summary_id, 'has_Rbc_Zbc: %d\n', has_boundary);

    if has_boundary
        fprintf(summary_id, 'nbcRZ: %d\n', boundary_count);
        fprintf(summary_id, 'Rbc_Zbc_signed_area: %.16e\n', ...
            boundary_area);
    end

    fprintf(summary_id, 'PNG: %s\n\n', png_file);

    fprintf('验证通过：%s\n', case_name);
end

clear summary_cleanup;

fprintf('\n');
fprintf('============================================================\n');
fprintf('两个 HDF5 文件均已通过 MATLAB 读取和基础网格检查。\n');
fprintf('汇总文件：%s\n', summary_file);
fprintf('请人工比较 standard_femmesh.png 与 linkmesh_mesh.png。\n');
fprintf('重点检查：网格形状、三角连接、外边界和异常跨域连线。\n');
fprintf('============================================================\n');