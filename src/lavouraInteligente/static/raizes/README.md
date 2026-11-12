# Mapa do Raízes

O mapa é renderizado localmente em SVG a partir dos polígonos GeoJSON cadastrados.
Os pontos são agrupados visualmente na escala nacional; ao ampliar, o polígono aparece
na mesma projeção dos demais elementos. Nenhuma imagem de satélite é simulada.

`brasil.geojson` contém a geometria do Brasil extraída do conjunto público
[Natural Earth, ne_110m_admin_0_countries](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson),
disponível em domínio público. O arquivo foi obtido em 11/11/2026 e é servido pelo
próprio Django. Não há envio das coordenadas de talhões para serviços de mapas.
