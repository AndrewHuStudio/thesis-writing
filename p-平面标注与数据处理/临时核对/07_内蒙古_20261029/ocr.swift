import Foundation
import Vision
import AppKit
let url=URL(fileURLWithPath:CommandLine.arguments[1])
let im=NSImage(contentsOf:url)!
var rect=NSRect(origin:.zero,size:im.size)
let cg=im.cgImage(forProposedRect:&rect,context:nil,hints:nil)!
let req=VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.recognitionLanguages=["zh-Hans","en-US"]
req.usesLanguageCorrection=false
try VNImageRequestHandler(cgImage:cg).perform([req])
for r in req.results ?? [] {
 let b=r.boundingBox
 print(String(format:"%.0f %.0f %.0f %.0f", b.minX*2444,(1-b.maxY)*3260,b.width*2444,b.height*3260),r.topCandidates(1).first!.string)
}
