/**
 * Produces an array of segments from two strings,
 * each segment tagged as 'equal', 'removed', or 'added'.
 * Used to render character-level diff highlighting.
 */
export function charDiff(oldStr, newStr) {
  // Split into words for more readable highlighting
  const oldWords = tokenise(oldStr)
  const newWords = tokenise(newStr)

  const matrix = buildLCS(oldWords, newWords)
  const ops    = backtrack(matrix, oldWords, newWords)

  return ops
}

function tokenise(str) {
  // Split on instruction boundaries — commas, spaces, brackets, semicolons
  return str.split(/(\s+|,|;|\(|\)|\[|\])/).filter(t => t.length > 0)
}

function buildLCS(a, b) {
  const m = a.length
  const n = b.length
  const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0))

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (a[i - 1] === b[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1])
      }
    }
  }
  return dp
}

function backtrack(dp, a, b) {
  const result = []
  let i = a.length
  let j = b.length

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && a[i - 1] === b[j - 1]) {
      result.unshift({ type: 'equal', text: a[i - 1] })
      i--
      j--
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i][j])) {
      result.unshift({ type: 'added', text: b[j - 1] })
      j--
    } else {
      result.unshift({ type: 'removed', text: a[i - 1] })
      i--
    }
  }
  return result
}