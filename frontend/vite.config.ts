import { defineConfig, loadEnv, type Connect } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

/**
 * Vite proxy /api/places-autocomplete → Google Places API New.
 *
 * Existe pra:
 * - Não expor GOOGLE_MAPS_API_KEY no bundle do frontend
 * - Dar uma camada de cache/rate-limit local em dev
 * - Servir como dev-time stand-in da futura Edge Function Supabase
 *
 * Em produção/dev com API rodando, o frontend chama
 * `${VITE_API_BASE}/api/places-autocomplete` (FastAPI em api.py).
 * Este middleware permanece como fallback local se alguém usar fetch relativo.
 */
function placesAutocompletePlugin() {
  return {
    name: 'places-autocomplete-proxy',
    configureServer(server: { middlewares: Connect.Server }) {
      const repoRoot = path.resolve(__dirname, '..')
      const env = {
        ...loadEnv('development', repoRoot, ''),
        ...loadEnv('development', process.cwd(), ''),
      }
      const apiKey = env.GOOGLE_MAPS_API_KEY || process.env.GOOGLE_MAPS_API_KEY

      server.middlewares.use(
        '/api/places-autocomplete',
        async (req, res) => {
          if (req.method !== 'POST') {
            res.statusCode = 405
            res.end(JSON.stringify({ error: 'POST only' }))
            return
          }
          if (!apiKey) {
            res.statusCode = 500
            res.end(
              JSON.stringify({
                error:
                  'GOOGLE_MAPS_API_KEY não definida — use .env na raiz do repo ou frontend/.env (mesma chave do FastAPI)',
              }),
            )
            return
          }
          try {
            const chunks: Buffer[] = []
            for await (const chunk of req) chunks.push(chunk as Buffer)
            const body = JSON.parse(Buffer.concat(chunks).toString('utf-8'))

            const { input, municipio, uf, lat, lng } = body as {
              input?: string
              municipio?: string
              uf?: string
              lat?: number
              lng?: number
            }
            // Permite input de 1 char QUANDO município está presente
            // (caso do useBairrosDoMunicipio que dispara "a", "b", "c"... em
            // paralelo pra cobrir todos bairros). Sem município, exige 2+.
            const minChars = municipio ? 1 : 2
            if (!input || input.length < minChars) {
              res.statusCode = 200
              res.setHeader('content-type', 'application/json')
              res.end(JSON.stringify({ suggestions: [] }))
              return
            }

            // Places API New :autocomplete — includedPrimaryTypes limita
            // a tipos de "bairro" (sublocality cobre bairro brasileiro,
            // neighborhood é o tipo Google legacy ainda aceito).
            //
            // Truque: prefixa município+UF ao input pra forçar fuzzy matching
            // dentro daquela cidade. Sem isso, "tama" retorna Tamanduateí/SP
            // ao invés de Tamatanduba/Eusébio.
            //
            // Ordem importa: "Eusebio, tama" funciona; "tama, Eusebio" volta
            // vazio. O algoritmo da Places API New trata o prefixo como
            // âncora geográfica e o resto como busca dentro dessa âncora.
            // locationBias seria a forma canônica mas exige geocode upfront.
            const queryString = municipio
              ? `${municipio}${uf ? ` ${uf}` : ''}, ${input}`.trim()
              : input
            const params: Record<string, unknown> = {
              input: queryString,
              languageCode: 'pt-BR',
              regionCode: 'BR',
              includedPrimaryTypes: ['sublocality', 'neighborhood'],
            }
            if (lat && lng) {
              params.locationBias = {
                circle: {
                  center: { latitude: lat, longitude: lng },
                  radius: 15000.0,
                },
              }
            }

            const upstream = await fetch(
              'https://places.googleapis.com/v1/places:autocomplete',
              {
                method: 'POST',
                headers: {
                  'content-type': 'application/json',
                  'x-goog-api-key': apiKey,
                  'x-goog-fieldmask':
                    'suggestions.placePrediction.placeId,suggestions.placePrediction.text,suggestions.placePrediction.structuredFormat',
                },
                body: JSON.stringify(params),
              },
            )
            // Log de debug — útil quando proxy retorna vazio mas API direta funciona.
            // Remover depois que estabilizar.
            console.log(
              `[places-autocomplete] query="${queryString}" status=${upstream.status}`,
            )
            const data = (await upstream.json()) as {
              suggestions?: Array<{
                placePrediction?: {
                  placeId?: string
                  text?: { text?: string }
                  structuredFormat?: {
                    mainText?: { text?: string }
                    secondaryText?: { text?: string }
                  }
                }
              }>
            }

            // Filtra a só sugestões dentro do município solicitado
            // (Places às vezes retorna bairros de cidades vizinhas mesmo
            // com locationBias quando o nome é ambíguo).
            //
            // Importante: comparação acento-tolerante. Caso clássico —
            // usuário digita "Eusebio" (sem acento), Places retorna
            // "Eusébio - CE" (com acento). includes() naive falha.
            const normalize = (s: string) =>
              s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
            const municipioNorm = normalize(municipio || '')
            const ufNorm = normalize(uf || '')
            const suggestions = (data.suggestions || [])
              .map((s) => {
                const pred = s.placePrediction
                if (!pred) return null
                const main = pred.structuredFormat?.mainText?.text || ''
                const secondary =
                  pred.structuredFormat?.secondaryText?.text || ''
                return {
                  placeId: pred.placeId || '',
                  bairro: main,
                  contexto: secondary,
                  textoCompleto: pred.text?.text || `${main}, ${secondary}`,
                }
              })
              .filter((s) => {
                if (!s) return false
                if (!municipioNorm) return true
                const fullNorm = normalize(`${s.contexto} ${s.textoCompleto}`)
                if (!fullNorm.includes(municipioNorm)) return false
                // UF é hint; Places costuma retornar "Ceará" em vez de "CE".
                return true
              })

            console.log(
              `[places-autocomplete] retornou ${suggestions.length}/${(data.suggestions || []).length} (filtro município "${municipio}")`,
            )

            res.statusCode = 200
            res.setHeader('content-type', 'application/json')
            res.end(JSON.stringify({ suggestions }))
          } catch (e) {
            res.statusCode = 500
            res.end(
              JSON.stringify({
                error: e instanceof Error ? e.message : String(e),
              }),
            )
          }
        },
      )
    },
  }
}

export default defineConfig({
  plugins: [react(), tailwindcss(), placesAutocompletePlugin()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      // Garante um único módulo de auth (evita useAuth fora de <AuthProvider> em prod).
      '@/lib/auth-context': path.resolve(__dirname, './src/lib/auth.tsx'),
    },
    dedupe: ['react', 'react-dom'],
  },
  server: {
    port: 5174,
    // strictPort false: se 5174 estiver em TIME_WAIT (após restart rápido),
    // Vite tenta 5175 automaticamente em vez de falhar com EADDRINUSE.
    strictPort: false,
  },
})
